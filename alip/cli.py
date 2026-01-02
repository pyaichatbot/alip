"""CLI entry point for ALIP."""

import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agents.ingestion import IngestionAgent
from core.models import EngagementConfig, AnalysisArtifact
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
        repo_artifact_path = ws.artifacts / "repo_inventory.json"
        db_artifact_path = ws.artifacts / "db_schema.json"
        
        if not repo_artifact_path.exists():
            console.print("[red]Error:[/red] Repository artifact not found")
            console.print("[yellow]Hint:[/yellow] Run ingestion first")
            sys.exit(1)
        
        # Load artifacts
        console.print("[yellow]→[/yellow] Loading artifacts...")
        with open(repo_artifact_path) as f:
            repo_data = json.load(f)
            repo_artifact = AnalysisArtifact(**repo_data)
        
        # Database artifact is optional
        if db_artifact_path.exists():
            with open(db_artifact_path) as f:
                db_data = json.load(f)
                db_artifact = AnalysisArtifact(**db_data)
            console.print(f"  [green]✓[/green] Database: {len(db_artifact.data.get('tables', []))} tables")
        else:
            # Create minimal database artifact if not provided
            console.print("  [dim]No database schema provided - creating minimal artifact[/dim]")
            db_artifact = AnalysisArtifact(
                artifact_type="db_schema",
                engagement_id=engagement,
                data={"tables": [], "indexes": [], "relationships": [], "database_name": "unknown"},
                sources=[],
                metrics={"total_tables": 0, "total_columns": 0}
            )
        
        # Display repository info (repo_inventory has different structure)
        repo_total_files = repo_artifact.data.get('total_files', 0) or repo_artifact.metrics.get('total_files', 0)
        console.print(f"  [green]✓[/green] Repository: {repo_total_files} files")
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
        
        # Run CostAnalysisAgent
        console.print("[yellow]→[/yellow] Cost analysis...")
        from agents.cost_analysis import CostAnalysisAgent
        
        try:
            # Load query logs artifact if available
            query_logs_artifact = None
            query_logs_path = ws.artifacts / "query_logs.json"
            if query_logs_path.exists():
                with open(query_logs_path) as f:
                    query_logs_data = json.load(f)
                    query_logs_artifact = AnalysisArtifact(**query_logs_data)
                console.print("  [dim]Query logs found[/dim]")
            else:
                console.print("  [dim]No query logs available - will create minimal artifact[/dim]")
            
            # Run cost analysis
            cost_agent = CostAnalysisAgent(ws, config)
            cost_artifact = cost_agent.analyze_costs(
                query_logs_artifact=query_logs_artifact,
                db_schema_artifact=db_artifact,
                topology_artifact=topology
            )
            
            # Display results
            summary = cost_artifact.data.get('summary', {})
            driver_count = summary.get('high_impact_count', 0) + summary.get('medium_impact_count', 0) + summary.get('low_impact_count', 0)
            
            console.print(f"  [green]✓[/green] Cost analysis complete:")
            console.print(f"    • {driver_count} cost drivers identified")
            if summary.get('high_impact_count', 0) > 0:
                console.print(f"    • {summary['high_impact_count']} high impact drivers")
            if summary.get('total_cost_ms', 0) > 0:
                total_cost_s = summary['total_cost_ms'] / 1000
                console.print(f"    • Total cost: {total_cost_s:.1f}s")
            
        except Exception as e:
            console.print(f"  [red]✗[/red] Cost analysis failed: {e}")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/dim]")
            # Continue with other analyses even if cost analysis fails
            console.print("  [yellow]Continuing with other analyses...[/yellow]\n")
        
        console.print()
        
        # Run RiskAnalysisAgent
        console.print("[yellow]→[/yellow] Risk assessment...")
        from agents.risk_analysis import RiskAnalysisAgent
        
        try:
            # Load documents artifact if available
            docs_artifact = None
            docs_artifact_path = ws.artifacts / "documents.json"
            if docs_artifact_path.exists():
                with open(docs_artifact_path) as f:
                    docs_data = json.load(f)
                    docs_artifact = AnalysisArtifact(**docs_data)
                console.print("  [dim]Documents found[/dim]")
            else:
                # Create minimal docs artifact
                docs_artifact = AnalysisArtifact(
                    artifact_type="documents",
                    engagement_id=engagement,
                    data={"documents": []},
                    sources=[],
                    metrics={"total_documents": 0}
                )
                console.print("  [dim]No documents available - will create minimal artifact[/dim]")
            
            # Run risk analysis
            risk_agent = RiskAnalysisAgent(ws, config)
            risk_artifact = risk_agent.analyze_risks(
                repo_artifact=repo_artifact,
                db_artifact=db_artifact,
                docs_artifact=docs_artifact,
                topology_artifact=topology
            )
            
            # Display results
            summary = risk_artifact.data.get('summary', {})
            total_risks = summary.get('total_risks', 0)
            critical_count = summary.get('critical_count', 0)
            high_count = summary.get('high_count', 0)
            
            console.print(f"  [green]✓[/green] Risk assessment complete:")
            console.print(f"    • {total_risks} risks identified")
            if critical_count > 0:
                console.print(f"    • {critical_count} critical risks")
            if high_count > 0:
                console.print(f"    • {high_count} high severity risks")
            
            # Show top risks
            risks = risk_artifact.data.get('risks', [])
            if risks:
                console.print(f"\n  [bold yellow]Top Risks:[/bold yellow]")
                for risk in risks[:3]:
                    severity = risk.get('severity', 'UNKNOWN')
                    title = risk.get('title', 'Unknown')
                    console.print(f"    • [{severity}] {title}")
            
        except Exception as e:
            console.print(f"  [red]✗[/red] Risk analysis failed: {e}")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/dim]")
            # Continue with other analyses even if risk analysis fails
            console.print("  [yellow]Continuing with other analyses...[/yellow]\n")
        
        console.print()
        
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
        
        # Load required artifacts
        console.print("[yellow]→[/yellow] Loading analysis artifacts...")
        
        topology_path = ws.artifacts / "topology.json"
        cost_path = ws.artifacts / "cost_drivers.json"
        risk_path = ws.artifacts / "risk_register.json"
        
        missing_artifacts = []
        if not topology_path.exists():
            missing_artifacts.append("topology")
        if not cost_path.exists():
            missing_artifacts.append("cost_drivers")
        if not risk_path.exists():
            missing_artifacts.append("risk_register")
        
        if missing_artifacts:
            console.print(f"[red]Error:[/red] Missing required artifacts: {', '.join(missing_artifacts)}")
            console.print(f"[yellow]Hint:[/yellow] Run analysis first: alip analyze --engagement {engagement}")
            sys.exit(1)
        
        # Load artifacts
        with open(topology_path) as f:
            topology_data = json.load(f)
            topology_artifact = AnalysisArtifact(**topology_data)
        
        with open(cost_path) as f:
            cost_data = json.load(f)
            cost_artifact = AnalysisArtifact(**cost_data)
        
        with open(risk_path) as f:
            risk_data = json.load(f)
            risk_artifact = AnalysisArtifact(**risk_data)
        
        console.print(f"  [green]✓[/green] Loaded {len(topology_artifact.data.get('statistics', {}))} topology metrics")
        console.print(f"  [green]✓[/green] Loaded {len(cost_artifact.data.get('cost_drivers', []))} cost drivers")
        console.print(f"  [green]✓[/green] Loaded {len(risk_artifact.data.get('risks', []))} risks\n")
        
        # Generate synthesis report
        console.print("[yellow]→[/yellow] Generating executive summary and reports...")
        from agents.synthesis import SynthesisAgent
        
        try:
            synthesis_agent = SynthesisAgent(ws, config)
            synthesis_artifact = synthesis_agent.generate_executive_summary(
                topology_artifact=topology_artifact,
                cost_artifact=cost_artifact,
                risk_artifact=risk_artifact
            )
            
            console.print(f"  [green]✓[/green] Executive summary generated")
            console.print(f"  [green]✓[/green] Technical appendix generated")
            console.print(f"  [green]✓[/green] Action plan generated")
            
            # Copy reports to reports directory
            import shutil
            
            exec_src = ws.artifacts / "executive_summary.md"
            exec_dst = ws.reports / "executive_summary.md"
            if exec_src.exists():
                shutil.copy2(exec_src, exec_dst)
            
            tech_src = ws.artifacts / "technical_appendix.md"
            tech_dst = ws.reports / "technical_appendix.md"
            if tech_src.exists():
                shutil.copy2(tech_src, tech_dst)
            
            action_src = ws.artifacts / "action_plan.md"
            action_dst = ws.reports / "action_plan.md"
            if action_src.exists():
                shutil.copy2(action_src, action_dst)
            
            # List all generated artifacts
            console.print(f"\n[bold green]✓ Report generation complete![/bold green]")
            console.print(f"\n[bold]Generated Reports:[/bold]")
            console.print(f"  • Executive Summary: {exec_dst}")
            console.print(f"  • Technical Appendix: {tech_dst}")
            console.print(f"  • Action Plan: {action_dst}")
            
            # List all artifacts
            artifact_files = list(ws.artifacts.glob('*'))
            console.print(f"\n[bold]All Artifacts ({len(artifact_files)} files):[/bold]")
            artifact_types = {
                'executive_summary.md': 'Executive Summary',
                'technical_appendix.md': 'Technical Appendix',
                'action_plan.md': 'Action Plan',
                'topology.md': 'System Topology',
                'cost_drivers.md': 'Cost Analysis',
                'risk_register.md': 'Risk Assessment',
            }
            
            for artifact_file in sorted(ws.artifacts.glob("*.md")):
                artifact_name = artifact_types.get(artifact_file.name, artifact_file.name)
                console.print(f"  • {artifact_name}: {artifact_file.name}")
            
            for artifact_file in sorted(ws.artifacts.glob("*.json")):
                console.print(f"  • {artifact_file.name}")
            
            if format == "pdf":
                console.print(f"\n[yellow]PDF export not yet implemented[/yellow]")
                console.print("Markdown reports available in reports directory")
            
        except Exception as e:
            console.print(f"  [red]✗[/red] Report generation failed: {e}")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/dim]")
            sys.exit(1)
        
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
