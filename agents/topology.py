"""TopologyAgent - System dependency graph construction."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from core.models import AnalysisArtifact, DependencyGraph, SourceReference
from core.skill_output import SkillOutput, create_skill_output

# Use production tree-sitter parser
from skills.tree_sitter_parser import TreeSitterExtractor, scan_directory_with_tree_sitter


class TopologyAgent:
    """Agent for building system topology and dependency graphs.
    
    Analyzes:
    - Code structure (modules, classes, functions)
    - Database dependencies (tables, queries)
    - Service dependencies (imports, calls)
    - Single points of failure (SPOFs)
    - Circular dependencies
    """

    def __init__(self, workspace_paths: Any, engagement_config: Any):
        """Initialize topology agent.
        
        Args:
            workspace_paths: WorkspacePaths object
            engagement_config: EngagementConfig object
        """
        self.workspace = workspace_paths
        self.config = engagement_config
        
        if not HAS_NETWORKX:
            raise ImportError(
                "networkx is required for TopologyAgent. "
                "Install with: pip install networkx"
            )

    def build_topology(
        self,
        repo_artifact: AnalysisArtifact,
        db_artifact: AnalysisArtifact,
    ) -> AnalysisArtifact:
        """Build system topology graph.
        
        Args:
            repo_artifact: Repository inventory artifact
            db_artifact: Database schema artifact
            
        Returns:
            AnalysisArtifact with dependency graph
        """
        # Initialize graph
        graph = nx.DiGraph()
        sources = []
        
        # 1. Extract modules from repository
        modules = self._extract_modules(repo_artifact, graph, sources)
        
        # 2. Extract tables from database
        tables = self._extract_tables(db_artifact, graph, sources)
        
        # 3. Analyze code for database dependencies
        self._analyze_code_db_dependencies(repo_artifact, graph, sources)
        
        # 4. Analyze module dependencies
        self._analyze_module_dependencies(repo_artifact, graph, sources)
        
        # 5. Calculate metrics
        metrics = self._calculate_metrics(graph)
        
        # 6. Detect SPOFs and issues
        spofs = self._detect_spofs(graph)
        circular = self._detect_circular_dependencies(graph)
        
        # 7. Build output data
        nodes = []
        for node_id in graph.nodes():
            node_data = graph.nodes[node_id]
            nodes.append({
                'id': node_id,
                'type': node_data.get('type', 'unknown'),
                'name': node_data.get('name', node_id),
                'metadata': node_data.get('metadata', {})
            })
        
        edges = []
        for source_id, target_id in graph.edges():
            edge_data = graph.edges[source_id, target_id]
            edges.append({
                'source': source_id,
                'target': target_id,
                'type': edge_data.get('type', 'uses'),
                'metadata': edge_data.get('metadata', {})
            })
        
        data = {
            'nodes': nodes,
            'edges': edges,
            'spofs': spofs,
            'circular_dependencies': circular,
            'statistics': {
                'total_nodes': len(nodes),
                'total_edges': len(edges),
                'modules': len(modules),
                'tables': len(tables),
                'spof_count': len(spofs)
            }
        }
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type='topology',
            engagement_id=self.config.engagement_id,
            data=data,
            sources=sources,
            metrics=metrics,
        )
        
        # Save artifact
        self._save_artifact(artifact)
        
        return artifact

    def _extract_modules(
        self,
        repo_artifact: AnalysisArtifact,
        graph: nx.DiGraph,
        sources: List[SourceReference]
    ) -> Set[str]:
        """Extract modules from repository and add to graph."""
        modules = set()
        repo_data = repo_artifact.data
        
        # Get files from repository inventory
        files = repo_data.get('files', [])
        
        for file_info in files:
            if file_info.get('extension') == '.py':
                # Create module node
                module_path = file_info['path']
                module_id = f"module:{module_path}"
                
                graph.add_node(
                    module_id,
                    type='module',
                    name=module_path,
                    metadata={
                        'lines': file_info.get('lines', 0),
                        'language': 'Python'
                    }
                )
                
                modules.add(module_id)
                
                # Add source reference
                sources.append(SourceReference(
                    type='repo',
                    path=module_path,
                    timestamp=datetime.now()
                ))
        
        return modules

    def _extract_tables(
        self,
        db_artifact: AnalysisArtifact,
        graph: nx.DiGraph,
        sources: List[SourceReference]
    ) -> Set[str]:
        """Extract database tables and add to graph."""
        tables = set()
        db_data = db_artifact.data
        
        # Get tables from database schema
        schema_tables = db_data.get('tables', [])
        
        for table_info in schema_tables:
            table_name = table_info['name']
            table_id = f"table:{table_name}"
            
            graph.add_node(
                table_id,
                type='table',
                name=table_name,
                metadata={
                    'columns': len(table_info.get('columns', [])),
                    'indexes': len(table_info.get('indexes', []))
                }
            )
            
            tables.add(table_id)
            
            # Add foreign key relationships
            for column in table_info.get('columns', []):
                if 'foreign_key' in column:
                    fk_table = column['foreign_key'].get('table')
                    if fk_table:
                        fk_table_id = f"table:{fk_table}"
                        graph.add_edge(
                            table_id,
                            fk_table_id,
                            type='references',
                            metadata={'column': column['name']}
                        )
            
            sources.append(SourceReference(
                type='db',
                path=f"schema/{table_name}",
                timestamp=datetime.now()
            ))
        
        return tables

    def _analyze_code_db_dependencies(
        self,
        repo_artifact: AnalysisArtifact,
        graph: nx.DiGraph,
        sources: List[SourceReference]
    ) -> None:
        """Analyze code for database access patterns."""
        repo_data = repo_artifact.data
        
        files = repo_data.get('files', [])
        
        for file_info in files:
            if file_info.get('extension') != '.py':
                continue
            
            module_path = file_info['path']
            module_id = f"module:{module_path}"
            
            # Check if module exists in graph
            if not graph.has_node(module_id):
                continue
            
            # Analyze SQL queries in metadata
            queries = file_info.get('sql_queries', [])
            
            for query in queries:
                table = query.get('table')
                if table:
                    table_id = f"table:{table}"
                    if graph.has_node(table_id):
                        graph.add_edge(
                            module_id,
                            table_id,
                            type='uses',
                            metadata={
                                'query_type': query.get('type', 'unknown'),
                                'line': query.get('line')
                            }
                        )

    def _analyze_module_dependencies(
        self,
        repo_artifact: AnalysisArtifact,
        graph: nx.DiGraph,
        sources: List[SourceReference]
    ) -> None:
        """Analyze module-to-module dependencies."""
        repo_data = repo_artifact.data
        files = repo_data.get('files', [])
        
        # Build module name map
        module_map = {}
        for file_info in files:
            if file_info.get('extension') == '.py':
                path = file_info['path']
                module_name = path.replace('/', '.').replace('.py', '')
                module_map[module_name] = f"module:{path}"
        
        # Analyze imports
        for file_info in files:
            if file_info.get('extension') != '.py':
                continue
            
            module_path = file_info['path']
            module_id = f"module:{module_path}"
            
            # Get imports from metadata
            imports = file_info.get('imports', [])
            
            for imported_module in imports:
                # Check if this is an internal import
                if imported_module in module_map:
                    target_id = module_map[imported_module]
                    if graph.has_node(target_id):
                        graph.add_edge(
                            module_id,
                            target_id,
                            type='imports',
                            metadata={'import': imported_module}
                        )

    def _calculate_metrics(self, graph: nx.DiGraph) -> Dict[str, Any]:
        """Calculate graph metrics."""
        metrics = {
            'node_count': graph.number_of_nodes(),
            'edge_count': graph.number_of_edges(),
            'density': nx.density(graph) if graph.number_of_nodes() > 0 else 0,
        }
        
        # Calculate centrality metrics
        if graph.number_of_nodes() > 0:
            try:
                degree_cent = nx.degree_centrality(graph)
                metrics['max_degree_centrality'] = max(degree_cent.values()) if degree_cent else 0
                
                between_cent = nx.betweenness_centrality(graph)
                metrics['max_betweenness_centrality'] = max(between_cent.values()) if between_cent else 0
            except:
                pass
        
        return metrics

    def _detect_spofs(self, graph: nx.DiGraph) -> List[Dict]:
        """Detect single points of failure in the graph."""
        spofs = []
        
        if graph.number_of_nodes() == 0:
            return spofs
        
        try:
            betweenness = nx.betweenness_centrality(graph)
            threshold = 0.1
            
            for node_id, centrality in betweenness.items():
                if centrality > threshold:
                    node_data = graph.nodes[node_id]
                    in_degree = graph.in_degree(node_id)
                    out_degree = graph.out_degree(node_id)
                    
                    spofs.append({
                        'node_id': node_id,
                        'node_type': node_data.get('type'),
                        'node_name': node_data.get('name'),
                        'betweenness_centrality': centrality,
                        'dependencies_count': in_degree + out_degree,
                        'risk_level': 'high' if centrality > 0.3 else 'medium'
                    })
            
            spofs.sort(key=lambda x: x['betweenness_centrality'], reverse=True)
        except Exception:
            pass
        
        return spofs

    def _detect_circular_dependencies(self, graph: nx.DiGraph) -> List[List[str]]:
        """Detect circular dependencies in the graph."""
        try:
            cycles = list(nx.simple_cycles(graph))
            cycles = [cycle for cycle in cycles if len(cycle) > 1]
            return cycles
        except Exception:
            return []

    def _save_artifact(self, artifact: AnalysisArtifact) -> None:
        """Save artifact to workspace."""
        json_path = self.workspace.artifacts / "topology.json"
        with open(json_path, 'w') as f:
            json.dump(artifact.model_dump(mode='json'), f, indent=2, default=str)
        
        md_path = self.workspace.artifacts / "topology.md"
        with open(md_path, 'w') as f:
            f.write(self._generate_markdown_summary(artifact))
        
        sources_path = self.workspace.artifacts / "topology_sources.json"
        with open(sources_path, 'w') as f:
            json.dump(
                {'sources': [s.model_dump(mode='json') for s in artifact.sources]},
                f,
                indent=2,
                default=str
            )
        
        metrics_path = self.workspace.artifacts / "topology_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(artifact.metrics, f, indent=2, default=str)

    def _generate_markdown_summary(self, artifact: AnalysisArtifact) -> str:
        """Generate human-readable markdown summary."""
        data = artifact.data
        stats = data['statistics']
        
        md = f"""# System Topology Analysis

**Engagement ID:** {artifact.engagement_id}
**Generated:** {artifact.created_at}

## Summary

- **Total Components:** {stats['total_nodes']}
- **Total Dependencies:** {stats['total_edges']}
- **Modules:** {stats['modules']}
- **Database Tables:** {stats['tables']}
- **Single Points of Failure:** {stats['spof_count']}

## Graph Metrics

"""
        
        for key, value in artifact.metrics.items():
            if isinstance(value, float):
                md += f"- **{key.replace('_', ' ').title()}:** {value:.3f}\n"
            else:
                md += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        
        spofs = data.get('spofs', [])
        if spofs:
            md += "\n## Single Points of Failure\n\n"
            for spof in spofs[:10]:
                md += f"- **{spof['node_name']}** ({spof['node_type']})\n"
                md += f"  - Risk Level: {spof['risk_level']}\n"
                md += f"  - Centrality: {spof['betweenness_centrality']:.3f}\n"
                md += f"  - Dependencies: {spof['dependencies_count']}\n\n"
        
        circular = data.get('circular_dependencies', [])
        if circular:
            md += f"\n## Circular Dependencies ({len(circular)} found)\n\n"
            for i, cycle in enumerate(circular[:5], 1):
                md += f"{i}. {' → '.join(cycle)} → {cycle[0]}\n"
        
        return md
