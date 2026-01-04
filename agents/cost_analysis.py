"""CostAnalysisAgent - Identify cost drivers in legacy systems.

This agent analyzes query logs, database schema, and system topology
to identify the top cost drivers and optimization opportunities.

Cost Calculation:
    total_cost = avg_duration_ms × frequency_per_day
    
Impact Classification:
    HIGH: > 10,000 ms/day (10+ seconds)
    MEDIUM: 1,000-10,000 ms/day (1-10 seconds)
    LOW: < 1,000 ms/day (< 1 second)
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.models import AnalysisArtifact, SourceReference, ConfidenceLevel
from core.llm.client import create_llm_client
from skills.database import parse_query_log


class CostAnalysisAgent:
    """Agent for analyzing system costs and optimization opportunities.
    
    This agent:
    1. Parses query logs to find slow/frequent queries
    2. Calculates total cost (duration × frequency)
    3. Detects missing indexes
    4. Analyzes patterns with LLM
    5. Ranks cost drivers by impact
    6. Generates actionable recommendations
    """

    def __init__(self, workspace: Any, config: Any):
        """Initialize cost analysis agent.
        
        Args:
            workspace: WorkspacePaths object
            config: EngagementConfig object
        """
        self.workspace = workspace
        self.config = config
        try:
            provider = getattr(config, 'llm_provider', 'claude')
            self.llm_client = create_llm_client(provider=provider)
        except (ValueError, Exception):
            # LLM client not available (e.g., missing API key in tests)
            self.llm_client = None

    def analyze_costs(
        self,
        query_logs_artifact: Optional[AnalysisArtifact],
        db_schema_artifact: AnalysisArtifact,
        topology_artifact: AnalysisArtifact,
    ) -> AnalysisArtifact:
        """Analyze system costs and identify top cost drivers.
        
        Args:
            query_logs_artifact: Query execution logs (optional)
            db_schema_artifact: Database schema
            topology_artifact: System topology
            
        Returns:
            AnalysisArtifact with top 10 cost drivers
        """
        # Step 1: Load query events
        if query_logs_artifact and query_logs_artifact.data.get('events'):
            query_events = query_logs_artifact.data['events']
        else:
            # No query logs - create minimal artifact
            return self._create_minimal_artifact(
                "No query logs available for cost analysis"
            )
        
        # Step 2: Aggregate queries by pattern
        query_stats = self._aggregate_query_stats(query_events)
        
        # Step 3: Calculate total costs
        cost_drivers = self._calculate_costs(query_stats)
        
        # Step 4: Detect missing indexes
        schema = db_schema_artifact.data
        cost_drivers = self._detect_missing_indexes(cost_drivers, schema)
        
        # Step 5: Enrich with topology context
        cost_drivers = self._enrich_with_topology(cost_drivers, topology_artifact)
        
        # Step 6: Analyze patterns with LLM
        cost_drivers = self._analyze_with_llm(cost_drivers, schema)
        
        # Step 7: Rank and select top 10
        top_drivers = sorted(
            cost_drivers,
            key=lambda x: x['total_cost_ms'],
            reverse=True
        )[:10]
        
        # Step 8: Create artifact
        return self._create_artifact(top_drivers, query_stats)

    def _aggregate_query_stats(
        self,
        query_events: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Aggregate query events by normalized pattern.
        
        Groups similar queries together (e.g., same query with different parameters).
        
        Args:
            query_events: List of query event dictionaries
            
        Returns:
            Dict mapping query pattern to aggregated stats
        """
        stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'pattern': '',
            'example_query': '',
            'count': 0,
            'total_duration_ms': 0.0,
            'min_duration_ms': float('inf'),
            'max_duration_ms': 0.0,
            'durations': [],
        })
        
        for event in query_events:
            # Normalize query to pattern (remove literals)
            query = event.get('query', '')
            pattern = self._normalize_query(query)
            
            duration = event.get('duration_ms', 0.0)
            
            # Update stats
            stat = stats[pattern]
            if not stat['pattern']:
                stat['pattern'] = pattern
                stat['example_query'] = query
            
            stat['count'] += 1
            stat['total_duration_ms'] += duration
            stat['min_duration_ms'] = min(stat['min_duration_ms'], duration)
            stat['max_duration_ms'] = max(stat['max_duration_ms'], duration)
            stat['durations'].append(duration)
        
        # Calculate averages
        for pattern, stat in stats.items():
            if stat['count'] > 0:
                stat['avg_duration_ms'] = stat['total_duration_ms'] / stat['count']
            else:
                stat['avg_duration_ms'] = 0.0
        
        return dict(stats)

    def _normalize_query(self, query: str) -> str:
        """Normalize query to pattern by removing literals.
        
        Examples:
            "SELECT * FROM users WHERE id = 123" -> "SELECT * FROM users WHERE id = ?"
            "SELECT * FROM orders WHERE user_id = 456" -> "SELECT * FROM orders WHERE user_id = ?"
        
        Args:
            query: Raw SQL query
            
        Returns:
            Normalized query pattern
        """
        # Remove string literals
        normalized = re.sub(r"'[^']*'", "'?'", query)
        
        # Remove numeric literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        
        # Convert to uppercase for consistency
        normalized = normalized.upper()
        
        return normalized

    def _calculate_costs(
        self,
        query_stats: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate total cost for each query pattern.
        
        Cost = avg_duration_ms × frequency
        
        Args:
            query_stats: Aggregated query statistics
            
        Returns:
            List of cost driver dictionaries
        """
        cost_drivers = []
        
        for pattern, stats in query_stats.items():
            # Calculate total cost (duration × frequency)
            total_cost_ms = stats['avg_duration_ms'] * stats['count']
            
            # Classify impact
            if total_cost_ms > 10000:  # > 10 seconds
                impact = 'HIGH'
            elif total_cost_ms > 1000:  # 1-10 seconds
                impact = 'MEDIUM'
            else:
                impact = 'LOW'
            
            # Extract table name
            table = self._extract_table_name(stats['example_query'])
            
            cost_driver = {
                'query_pattern': pattern,
                'example_query': stats['example_query'],
                'table': table,
                'execution_count': stats['count'],
                'avg_duration_ms': round(stats['avg_duration_ms'], 2),
                'min_duration_ms': round(stats['min_duration_ms'], 2),
                'max_duration_ms': round(stats['max_duration_ms'], 2),
                'total_cost_ms': round(total_cost_ms, 2),
                'impact': impact,
                'missing_indexes': [],
                'recommendations': [],
                'affected_components': [],
            }
            
            cost_drivers.append(cost_driver)
        
        return cost_drivers

    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from SQL query.
        
        Args:
            query: SQL query string
            
        Returns:
            Table name or None
        """
        query_upper = query.upper()
        
        # FROM clause
        from_match = re.search(r'FROM\s+(\w+)', query_upper)
        if from_match:
            return from_match.group(1).lower()
        
        # INTO clause
        into_match = re.search(r'INTO\s+(\w+)', query_upper)
        if into_match:
            return into_match.group(1).lower()
        
        # UPDATE clause
        update_match = re.search(r'UPDATE\s+(\w+)', query_upper)
        if update_match:
            return update_match.group(1).lower()
        
        return None

    def _detect_missing_indexes(
        self,
        cost_drivers: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect missing indexes that could improve query performance.
        
        Checks WHERE clauses against existing indexes.
        
        Args:
            cost_drivers: List of cost drivers
            schema: Database schema
            
        Returns:
            Updated cost drivers with missing_indexes field
        """
        # Build index map: table -> [indexed_columns]
        index_map: Dict[str, List[str]] = defaultdict(list)
        
        tables = schema.get('tables', [])
        for table in tables:
            table_name = table.get('name', '').lower()
            indexes = table.get('indexes', [])
            
            for index in indexes:
                columns = index.get('columns', [])
                for col in columns:
                    index_map[table_name].append(col.lower())
        
        # Check each cost driver
        for driver in cost_drivers:
            table = driver.get('table')
            if not table:
                continue
            
            query = driver['example_query']
            
            # Extract WHERE clause columns
            where_columns = self._extract_where_columns(query)
            
            # Check if columns are indexed
            indexed_columns = set(index_map.get(table, []))
            missing = [col for col in where_columns if col not in indexed_columns]
            
            if missing:
                driver['missing_indexes'] = missing
                
                # Add recommendation
                if len(missing) == 1:
                    rec = f"Consider adding index on {table}.{missing[0]}"
                else:
                    cols = ', '.join(missing)
                    rec = f"Consider adding composite index on {table}({cols})"
                
                driver['recommendations'].append(rec)
        
        return cost_drivers

    def _extract_where_columns(self, query: str) -> List[str]:
        """Extract column names from WHERE clause.
        
        Args:
            query: SQL query
            
        Returns:
            List of column names
        """
        columns = []
        
        # Find WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:GROUP BY|ORDER BY|LIMIT|;|$)', query, re.IGNORECASE)
        if not where_match:
            return columns
        
        where_clause = where_match.group(1)
        
        # Extract column names (simplified - production would use SQL parser)
        # Pattern: column_name = ? or column_name IN (...)
        col_matches = re.findall(r'(\w+)\s*(?:=|IN|>|<|>=|<=|!=|<>)', where_clause, re.IGNORECASE)
        
        columns = [col.lower() for col in col_matches if col.upper() not in ['AND', 'OR', 'NOT']]
        
        return columns

    def _enrich_with_topology(
        self,
        cost_drivers: List[Dict[str, Any]],
        topology_artifact: AnalysisArtifact
    ) -> List[Dict[str, Any]]:
        """Enrich cost drivers with topology information.
        
        Adds information about which components access each table.
        
        Args:
            cost_drivers: List of cost drivers
            topology_artifact: System topology
            
        Returns:
            Updated cost drivers with affected_components
        """
        topology = topology_artifact.data
        edges = topology.get('edges', [])
        nodes = topology.get('nodes', [])
        
        # Build map: table -> [modules that use it]
        table_users: Dict[str, List[str]] = defaultdict(list)
        
        for edge in edges:
            if edge.get('type') == 'uses':
                target = edge.get('target', '')
                source = edge.get('source', '')
                
                # Extract table name from target (format: "table:tablename")
                if target.startswith('table:'):
                    table_name = target.split(':', 1)[1]
                    
                    # Extract module name from source
                    if source.startswith('module:'):
                        module_name = source.split(':', 1)[1]
                        table_users[table_name].append(module_name)
        
        # Update cost drivers
        for driver in cost_drivers:
            table = driver.get('table')
            if table and table in table_users:
                driver['affected_components'] = table_users[table]
        
        return cost_drivers

    def _analyze_with_llm(
        self,
        cost_drivers: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to analyze cost drivers and generate recommendations.
        
        Args:
            cost_drivers: List of cost drivers
            schema: Database schema
            
        Returns:
            Updated cost drivers with LLM-generated recommendations
        """
        if not cost_drivers:
            return cost_drivers
        
        # Load system prompt
        prompt_path = Path(__file__).parent.parent / "prompts" / "cost_analysis" / "system_prompt_v1.md"
        
        if not prompt_path.exists():
            # Fallback: skip LLM analysis
            return cost_drivers
        
        with open(prompt_path) as f:
            system_prompt = f.read()
        
        # Analyze top 3 cost drivers with LLM
        for i, driver in enumerate(cost_drivers[:3]):
            try:
                # Prepare context
                context = {
                    'query': driver['example_query'],
                    'table': driver.get('table'),
                    'execution_count': driver['execution_count'],
                    'avg_duration_ms': driver['avg_duration_ms'],
                    'missing_indexes': driver.get('missing_indexes', []),
                }
                
                user_message = f"""Analyze this query performance issue:

Query: {context['query']}
Table: {context['table']}
Executions: {context['execution_count']}
Avg Duration: {context['avg_duration_ms']}ms
Missing Indexes: {context['missing_indexes']}

Provide specific optimization recommendations."""
                
                # Call LLM
                response = self.llm_client.generate(
                    prompt=user_message,
                    system=system_prompt,
                    max_tokens=500
                )
                
                # Extract recommendations from response
                recommendations = self._extract_recommendations(response)
                
                # Add to existing recommendations
                driver['recommendations'].extend(recommendations)
                
            except Exception as e:
                # Continue on error - don't fail entire analysis
                driver['recommendations'].append(
                    f"LLM analysis unavailable: {str(e)}"
                )
        
        return cost_drivers

    def _extract_recommendations(self, llm_response: str) -> List[str]:
        """Extract actionable recommendations from LLM response.
        
        Args:
            llm_response: LLM generated text
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Look for bullet points or numbered lists
        lines = llm_response.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Match bullet points or numbers
            if re.match(r'^[\d\-\*•]\s*\.?\s+', line):
                # Remove bullet/number
                rec = re.sub(r'^[\d\-\*•]\s*\.?\s+', '', line)
                if rec and len(rec) > 10:  # Filter out too short
                    recommendations.append(rec)
        
        # If no bullets found, try to extract sentences with optimization keywords
        if not recommendations:
            keywords = ['optimize', 'improve', 'add', 'remove', 'consider', 'recommend', 'suggest']
            for line in lines:
                if any(keyword in line.lower() for keyword in keywords):
                    recommendations.append(line.strip())
        
        return recommendations[:3]  # Max 3 recommendations per query

    def _create_artifact(
        self,
        cost_drivers: List[Dict[str, Any]],
        query_stats: Dict[str, Dict[str, Any]]
    ) -> AnalysisArtifact:
        """Create cost analysis artifact.
        
        Args:
            cost_drivers: Top cost drivers
            query_stats: Query statistics
            
        Returns:
            AnalysisArtifact
        """
        # Calculate summary statistics
        total_queries = sum(stats['count'] for stats in query_stats.values())
        total_cost_ms = sum(driver['total_cost_ms'] for driver in cost_drivers)
        
        high_impact = len([d for d in cost_drivers if d['impact'] == 'HIGH'])
        medium_impact = len([d for d in cost_drivers if d['impact'] == 'MEDIUM'])
        low_impact = len([d for d in cost_drivers if d['impact'] == 'LOW'])
        
        # Create artifact data
        data = {
            'cost_drivers': cost_drivers,
            'summary': {
                'total_queries_analyzed': total_queries,
                'unique_query_patterns': len(query_stats),
                'total_cost_ms': round(total_cost_ms, 2),
                'high_impact_count': high_impact,
                'medium_impact_count': medium_impact,
                'low_impact_count': low_impact,
            }
        }
        
        # Create source references
        sources = [
            SourceReference(
                type='query_logs',
                path='query_logs.json',
                timestamp=datetime.now()
            ),
            SourceReference(
                type='db_schema',
                path='database.json',
                timestamp=datetime.now()
            )
        ]
        
        # Create metrics
        metrics = {
            'driver_count': len(cost_drivers),
            'total_cost_ms': round(total_cost_ms, 2),
            'queries_analyzed': total_queries,
        }
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type='cost_drivers',
            engagement_id=self.config.engagement_id,
            data=data,
            sources=sources,
            metrics=metrics,
            confidence=ConfidenceLevel.HIGH  # High confidence from actual query logs
        )
        
        # Save artifacts
        self._save_artifacts(artifact, cost_drivers)
        
        return artifact

    def _create_minimal_artifact(self, note: str) -> AnalysisArtifact:
        """Create minimal artifact when query logs are unavailable.
        
        Args:
            note: Explanation message
            
        Returns:
            AnalysisArtifact with empty cost drivers
        """
        data = {
            'cost_drivers': [],
            'summary': {
                'total_queries_analyzed': 0,
                'unique_query_patterns': 0,
                'total_cost_ms': 0,
                'high_impact_count': 0,
                'medium_impact_count': 0,
                'low_impact_count': 0,
            },
            'note': note
        }
        
        artifact = AnalysisArtifact(
            artifact_type='cost_drivers',
            engagement_id=self.config.engagement_id,
            data=data,
            sources=[],
            metrics={'driver_count': 0},
            confidence=ConfidenceLevel.LOW
        )
        
        # Save minimal artifacts
        self._save_artifacts(artifact, [])
        
        return artifact

    def _save_artifacts(
        self,
        artifact: AnalysisArtifact,
        cost_drivers: List[Dict[str, Any]]
    ) -> None:
        """Save cost analysis artifacts to workspace.
        
        Args:
            artifact: Main artifact
            cost_drivers: Cost driver list
        """
        # Save main artifact
        artifact_path = self.workspace.artifacts / "cost_drivers.json"
        with open(artifact_path, 'w') as f:
            json.dump(artifact.model_dump(mode='json'), f, indent=2, default=str)
        
        # Save markdown summary
        md_path = self.workspace.artifacts / "cost_drivers.md"
        self._generate_markdown(cost_drivers, md_path)
        
        # Save sources
        sources_path = self.workspace.artifacts / "cost_drivers_sources.json"
        with open(sources_path, 'w') as f:
            json.dump(
                [s.model_dump(mode='json') for s in artifact.sources],
                f,
                indent=2,
                default=str
            )
        
        # Save metrics
        metrics_path = self.workspace.artifacts / "cost_drivers_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(artifact.metrics, f, indent=2)

    def _generate_markdown(
        self,
        cost_drivers: List[Dict[str, Any]],
        output_path: Path
    ) -> None:
        """Generate human-readable markdown summary.
        
        Args:
            cost_drivers: Cost driver list
            output_path: Path to save markdown
        """
        lines = [
            "# Cost Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Engagement:** {self.config.client_name}",
            "",
            "## Summary",
            "",
            f"- **Total Cost Drivers Identified:** {len(cost_drivers)}",
        ]
        
        if cost_drivers:
            high = len([d for d in cost_drivers if d['impact'] == 'HIGH'])
            medium = len([d for d in cost_drivers if d['impact'] == 'MEDIUM'])
            low = len([d for d in cost_drivers if d['impact'] == 'LOW'])
            
            lines.extend([
                f"- **High Impact:** {high}",
                f"- **Medium Impact:** {medium}",
                f"- **Low Impact:** {low}",
                "",
                "## Top Cost Drivers",
                ""
            ])
            
            for i, driver in enumerate(cost_drivers, 1):
                lines.extend([
                    f"### {i}. {driver['table'] or 'Unknown Table'} ({driver['impact']} Impact)",
                    "",
                    f"**Query Pattern:**",
                    f"```sql",
                    driver['query_pattern'][:200],
                    f"```",
                    "",
                    f"**Metrics:**",
                    f"- Execution Count: {driver['execution_count']:,}",
                    f"- Avg Duration: {driver['avg_duration_ms']:.2f}ms",
                    f"- Total Cost: {driver['total_cost_ms']:.2f}ms",
                    "",
                ])
                
                if driver.get('missing_indexes'):
                    lines.extend([
                        f"**Missing Indexes:**",
                        *[f"- {idx}" for idx in driver['missing_indexes']],
                        "",
                    ])
                
                if driver.get('recommendations'):
                    lines.extend([
                        f"**Recommendations:**",
                        *[f"- {rec}" for rec in driver['recommendations'][:3]],
                        "",
                    ])
                
                if driver.get('affected_components'):
                    lines.extend([
                        f"**Affected Components:**",
                        *[f"- {comp}" for comp in driver['affected_components'][:5]],
                        "",
                    ])
        else:
            lines.extend([
                "",
                "*No cost drivers identified. Query logs may not be available.*",
                ""
            ])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
