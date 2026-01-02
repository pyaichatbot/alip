"""CLI entry point for ALIP."""

import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents.ingestion import IngestionAgent
from core.models import EngagementConfig
from skills.workspace import (
    init_workspace,
    load_engagement_config,
    load_workspace,
    save_engagement_config,
)

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """ALIP - AI-Assisted Legacy Intelligence Platform.
    
    Trust-first, read-only analysis for legacy systems.
    """
    pass


@main.command()
@click.option("--name", required=True, help="Client/company name")
@click.option("--id", "engagement_id", required=True, help="Unique engagement ID")
@click.option("--locale", default="en", help="Locale (en, de, etc.)")
@click.option("--workspace", default="./workspace", help="Workspace base directory")
def new(name: str, engagement_id: str, locale: str, workspace: str) -> None:
    """Create a new engagement workspace."""
    try:
        console.print(f"\n[bold blue]Creating new engagement:[/bold blue] {name} ({engagement_id})")
        
        workspace_path = Path(workspace)
        ws = init_workspace(
            engagement_id=engagement_id,
            client_name=name,
            base_dir=workspace_path,
            config_overrides={"locale": locale},
        )
        
        console.print(f"\n[green]✓[/green] Workspace created: {ws.root}")
        console.print("\n[bold]Directory Structure:[/bold]")
        console.print(f"  • Config:     {ws.config}")
        console.print(f"  • Raw:        {ws.raw}")
        console.print(f"  • Processed:  {ws.processed}")
        console.print(f"  • Artifacts:  {ws.artifacts}")
        console.print(f"  • Reports:    {ws.reports}")
        
        console.print(f"\n[bold green]Next steps:[/bold green]")
        console.print(f"  1. alip ingest --engagement {engagement_id} --repo <path>")
        console.print(f"  2. alip analyze --engagement {engagement_id}")
        console.print(f"  3. alip report --engagement {engagement_id}")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.option("--engagement", required=True, help="Engagement ID")
@click.option("--repo", type=click.Path(exists=True), help="Repository path")
@click.option("--db-schema", type=click.Path(exists=True), help="Database schema file")
@click.option("--query-logs", type=click.Path(exists=True), help="Query log file")
@click.option("--docs", type=click.Path(exists=True), help="Documentation directory")
@click.option("--workspace", default="./workspace", help="Workspace base directory")
def ingest(
    engagement: str,
    repo: str | None,
    db_schema: str | None,
    query_logs: str | None,
    docs: str | None,
    workspace: str,
) -> None:
    """Ingest data sources for analysis."""
    try:
        from core.state_machine import EngagementState, StateViolationError, validate_transition
        
        # Load workspace
        ws = load_workspace(engagement, Path(workspace))
        config = load_engagement_config(ws)
        
        # Validate state transition
        try:
            validate_transition(
                current=EngagementState(config.state),
                target=EngagementState.INGESTED,
            )
        except StateViolationError as e:
            console.print(f"\n[bold red]State Violation:[/bold red] {e}")
            console.print(f"\n[yellow]Current state:[/yellow] {config.state}")
            console.print(f"[yellow]Cannot transition to:[/yellow] ingested")
            sys.exit(1)
        
        # Enforce read-only mode
        if not config.read_only_mode:
            console.print("\n[bold red]Security Error:[/bold red] Read-only mode is disabled")
            console.print("ALIP must operate in read-only mode for safety")
            sys.exit(1)
        
        console.print(f"\n[bold blue]Ingesting data for:[/bold blue] {config.client_name}")
        console.print(f"[dim]Engagement ID: {engagement}[/dim]")
        console.print(f"[dim]Current state: {config.state}[/dim]")
        console.print(f"[green]✓ Read-only mode: ENFORCED[/green]\n")
        
        # Initialize ingestion agent
        agent = IngestionAgent(ws, config)
        
        # Track what was ingested
        ingested = []
        
        # Ingest repository
        if repo:
            console.print("[yellow]→[/yellow] Ingesting repository...")
            artifact = agent.ingest_repository(Path(repo))
            console.print(f"  [green]✓[/green] Repository: {artifact.metrics.get('total_files')} files")
            ingested.append("repo")
        
        # Ingest database schema
        if db_schema:
            console.print("[yellow]→[/yellow] Ingesting database schema...")
            artifact = agent.ingest_database_schema(Path(db_schema))
            console.print(f"  [green]✓[/green] Schema: {artifact.metrics.get('total_tables')} tables")
            ingested.append("db_schema")
        
        # Ingest query logs
        if query_logs:
            console.print("[yellow]→[/yellow] Ingesting query logs...")
            artifact = agent.ingest_query_logs(Path(query_logs))
            console.print(f"  [green]✓[/green] Queries: {artifact.metrics.get('total_queries')} logged")
            ingested.append("query_logs")
        
        # Ingest documents
        if docs:
            console.print("[yellow]→[/yellow] Ingesting documents...")
            artifact = agent.ingest_documents(Path(docs))
            console.print(f"  [green]✓[/green] Documents: {artifact.metrics.get('total_documents')} files")
            ingested.append("docs")
        
        if not any([repo, db_schema, query_logs, docs]):
            console.print("[red]Error:[/red] No data sources specified")
            console.print("Use --repo, --db-schema, --query-logs, or --docs")
            sys.exit(1)
        
        # Update engagement state
        config.update_state(EngagementState.INGESTED.value)
        save_engagement_config(ws, config)
        
        console.print(f"\n[green]✓[/green] Ingestion complete")
        console.print(f"[dim]Artifacts saved to: {ws.artifacts}[/dim]")
        console.print(f"[dim]Ingested: {', '.join(ingested)}[/dim]")
        console.print(f"[bold green]State updated:[/bold green] {config.state}")
        console.print(f"\n[bold]Next step:[/bold] alip analyze --engagement {engagement}")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@main.command()
@click.option("--engagement", required=True, help="Engagement ID")
@click.option("--workspace", default="./workspace", help="Workspace base directory")
def analyze(engagement: str, workspace: str) -> None:
    """Run analysis on ingested data."""
    try:
        from core.state_machine import EngagementState, StateViolationError, validate_transition
        from agents.topology import TopologyAgent
        from core.models import AnalysisArtifact
        import json
        
        # Load workspace
        ws = load_workspace(engagement, Path(workspace))
        config = load_engagement_config(ws)
        
        # Validate state transition
        try:
            validate_transition(
                current=EngagementState(config.state),
                target=EngagementState.ANALYZED,
            )
        except StateViolationError as e:
            console.print(f"\n[bold red]State Violation:[/bold red] {e}")
            console.print(f"\n[yellow]Current state:[/yellow] {config.state}")
            sys.exit(1)
        
        console.print(f"\n[bold blue]Analyzing engagement:[/bold blue] {config.client_name}")
        console.print(f"[dim]Engagement ID: {engagement}[/dim]")
        console.print(f"[dim]Current state: {config.state}[/dim]\n")
        
        # Load artifacts from ingestion
        repo_artifact_path = ws.artifacts / "repository.json"
        db_artifact_path = ws.artifacts / "database.json"
        
        if not repo_artifact_path.exists():
            console.print("[red]Error:[/red] Repository artifact not found")
            console.print("[yellow]Hint:[/yellow] Run ingestion first")
            sys.exit(1)
        
        if not db_artifact_path.exists():
            console.print("[red]Error:[/red] Database artifact not found")
            console.print("[yellow]Hint:[/yellow] Run ingestion with --db-schema")
            sys.exit(1)
        
        # Load artifacts
        console.print("[yellow]→[/yellow] Loading artifacts...")
        with open(repo_artifact_path) as f:
            repo_data = json.load(f)
            repo_artifact = AnalysisArtifact(**repo_data)
        
        with open(db_artifact_path) as f:
            db_data = json.load(f)
            db_artifact = AnalysisArtifact(**db_data)
        
        console.print(f"  [green]✓[/green] Repository: {len(repo_artifact.data.get('files', []))} files")
        console.print(f"  [green]✓[/green] Database: {len(db_artifact.data.get('tables', []))} tables\n")
        
        # Run TopologyAgent
        console.print("[yellow]→[/yellow] Building system topology...")
        topology_agent = TopologyAgent(ws, config)
        
        try:
            topology = topology_agent.build_topology(repo_artifact, db_artifact)
            
            stats = topology.data['statistics']
            console.print(f"  [green]✓[/green] Topology complete:")
            console.print(f"    • {stats['total_nodes']} components")
            console.print(f"    • {stats['total_edges']} dependencies")
            console.print(f"    • {stats['spof_count']} SPOFs detected")
            
            # Show top SPOFs
            spofs = topology.data.get('spofs', [])
            if spofs:
                console.print(f"\n  [bold yellow]Top SPOFs:[/bold yellow]")
                for spof in spofs[:3]:
                    console.print(f"    • {spof['node_name']} ({spof['node_type']}) - {spof['risk_level']} risk")
            
        except ImportError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            console.print("\n[yellow]Missing dependency:[/yellow] NetworkX is required")
            console.print("Install with: pip install networkx")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]Error during topology analysis:[/red] {e}")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)
        
        console.print()
        
        # TODO: Run other analysis agents (cost, risk, synthesis)
        # For now, create stub artifacts for them
        console.print("[yellow]→[/yellow] Cost analysis...")
        console.print("  [dim](Using stub - CostAnalysisAgent not yet implemented)[/dim]")
        
        from core.models import SourceReference
        cost_drivers = AnalysisArtifact(
            artifact_type="cost_drivers",
            engagement_id=engagement,
            data={
                "drivers": [],
                "note": "Stub artifact - CostAnalysisAgent in development"
            },
            sources=[SourceReference(type="system", path="stub", timestamp=datetime.now())],
            metrics={"driver_count": 0},
        )
        cost_path = ws.artifacts / "cost_drivers.json"
        with open(cost_path, "w") as f:
            json.dump(cost_drivers.model_dump(mode="json"), f, indent=2, default=str)
        console.print(f"  [green]✓[/green] Cost analysis: stub created\n")
        
        console.print("[yellow]→[/yellow] Risk assessment...")
        console.print("  [dim](Using stub - RiskAnalysisAgent not yet implemented)[/dim]")
        
        risk_register = AnalysisArtifact(
            artifact_type="risk_register",
            engagement_id=engagement,
            data={
                "risks": [],
                "note": "Stub artifact - RiskAnalysisAgent in development"
            },
            sources=[SourceReference(type="system", path="stub", timestamp=datetime.now())],
            metrics={"risk_count": 0},
        )
        risk_path = ws.artifacts / "risk_register.json"
        with open(risk_path, "w") as f:
            json.dump(risk_register.model_dump(mode="json"), f, indent=2, default=str)
        console.print(f"  [green]✓[/green] Risk assessment: stub created\n")
        
        # Update engagement state
        config.update_state(EngagementState.ANALYZED.value)
        save_engagement_config(ws, config)
        
        console.print(f"[bold green]✓ Analysis complete![/bold green]")
        console.print(f"[dim]Artifacts saved in: {ws.artifacts}/[/dim]")
        console.print(f"[bold green]State updated:[/bold green] {config.state}")
        console.print(f"\n[bold]Next step:[/bold] alip report --engagement {engagement}")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@main.command()
@click.option("--engagement", required=True, help="Engagement ID")
@click.option("--format", type=click.Choice(["md", "pdf"]), default="md", help="Report format")
@click.option("--workspace", default="./workspace", help="Workspace base directory")
def report(engagement: str, format: str, workspace: str) -> None:
    """Generate reports from analysis."""
    try:
        from core.state_machine import EngagementState
        import json
        
        # Load workspace
        ws = load_workspace(engagement, Path(workspace))
        config = load_engagement_config(ws)
        
        console.print(f"\n[bold blue]Generating report for:[/bold blue] {config.client_name}")
        console.print(f"[dim]Engagement ID: {engagement}[/dim]")
        console.print(f"[dim]Current state: {config.state}[/dim]\n")
        
        if config.state not in ["analyzed", "reviewed", "finalized"]:
            console.print(f"[red]Error:[/red] Must analyze before generating report")
            console.print(f"[yellow]Current state:[/yellow] {config.state}")
            console.print(f"\nRun: alip analyze --engagement {engagement}")
            sys.exit(1)
        
        console.print("[yellow]⚠ Using minimal stub report (SynthesisAgent not yet implemented)[/yellow]\n")
        
        # Generate minimal markdown report
        report_content = f"""# ALIP Analysis Report

**Client:** {config.client_name}
**Engagement ID:** {engagement}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**State:** {config.state}

---

## Summary

This is a stub report. Full report generation requires SynthesisAgent implementation.

## Artifacts Available

"""
        
        # List available artifacts
        artifact_files = list(ws.artifacts.glob("*.json"))
        for artifact_file in artifact_files:
            with open(artifact_file) as f:
                artifact_data = json.load(f)
            artifact_type = artifact_data.get("artifact_type", "unknown")
            report_content += f"- **{artifact_type}**: `{artifact_file.name}`\n"
        
        report_content += f"""

---

## Next Steps

1. Review artifacts in `{ws.artifacts}/`
2. Implement Phase 2 agents for full analysis
3. Generate executive summary with SynthesisAgent

See IMPLEMENTATION_STATUS.md for details.
"""
        
        # Save report
        report_path = ws.reports / f"report_{engagement}.md"
        with open(report_path, "w") as f:
            f.write(report_content)
        
        console.print(f"[green]✓[/green] Report generated: {report_path}")
        
        if format == "pdf":
            console.print(f"\n[yellow]PDF export not yet implemented[/yellow]")
            console.print("Markdown report available at the path above")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@main.command()
@click.option("--engagement", required=True, help="Engagement ID")
@click.option("--workspace", default="./workspace", help="Workspace base directory")
def run(engagement: str, workspace: str) -> None:
    """Run complete analysis pipeline (ingest must be done first)."""
    try:
        # Load workspace
        ws = load_workspace(engagement, Path(workspace))
        config = load_engagement_config(ws)
        
        console.print(f"\n[bold blue]Running complete pipeline for:[/bold blue] {config.client_name}")
        console.print(f"[dim]Engagement ID: {engagement}[/dim]")
        console.print(f"[dim]Current state: {config.state}[/dim]\n")
        
        # Check that ingestion is done
        if config.state == "new":
            console.print(f"[red]Error:[/red] Must ingest data first")
            console.print(f"\nRun: alip ingest --engagement {engagement} --repo <path>")
            sys.exit(1)
        
        # Run analysis if not already done
        if config.state in ["new", "ingested"]:
            console.print("[bold]Step 1: Analysis[/bold]")
            from click.testing import CliRunner
            runner = CliRunner()
            result = runner.invoke(analyze, ["--engagement", engagement, "--workspace", workspace])
            if result.exit_code != 0:
                console.print("[red]Analysis failed[/red]")
                sys.exit(1)
        
        # Generate report
        console.print("\n[bold]Step 2: Report Generation[/bold]")
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(report, ["--engagement", engagement, "--workspace", workspace])
        if result.exit_code != 0:
            console.print("[red]Report generation failed[/red]")
            sys.exit(1)
        
        console.print(f"\n[bold green]✓ Pipeline complete![/bold green]")
        console.print(f"\nOutputs:")
        console.print(f"  • Artifacts: {ws.artifacts}/")
        console.print(f"  • Report: {ws.reports}/")
        console.print(f"\n[yellow]Note:[/yellow] This uses stub analysis. Full pipeline requires Phase 2 agents.")
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


@main.command()
@click.option("--workspace", default="./workspace", help="Workspace base directory")
def list(workspace: str) -> None:
    """List all engagements."""
    workspace_path = Path(workspace)
    
    if not workspace_path.exists():
        console.print(f"\n[yellow]No workspace found at:[/yellow] {workspace_path}")
        return
    
    engagements = [d for d in workspace_path.iterdir() if d.is_dir()]
    
    if not engagements:
        console.print(f"\n[yellow]No engagements found in:[/yellow] {workspace_path}")
        return
    
    table = Table(title="ALIP Engagements")
    table.add_column("Engagement ID", style="cyan")
    table.add_column("Client Name", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Locale", style="blue")
    
    for eng_dir in sorted(engagements):
        try:
            ws = load_workspace(eng_dir.name, workspace_path)
            config = load_engagement_config(ws)
            table.add_row(
                config.engagement_id,
                config.client_name,
                config.created_at.strftime("%Y-%m-%d %H:%M"),
                config.locale,
            )
        except Exception:
            continue
    
    console.print()
    console.print(table)
    console.print()


if __name__ == "__main__":
    main()
