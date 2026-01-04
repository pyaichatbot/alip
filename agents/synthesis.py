"""SynthesisAgent - Generate executive summaries and final reports.

This agent consolidates all analysis artifacts into executive-ready deliverables:
- Executive Summary (2-3 pages)
- Technical Appendix (detailed findings)
- Prioritized Recommendations
- Action Plan

The output is designed for C-level executives and technical leadership.
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.models import AnalysisArtifact, SourceReference, ConfidenceLevel
from core.llm.client import create_llm_client


class SynthesisAgent:
    """Agent for synthesizing all analysis into executive deliverables.
    
    This agent:
    1. Consolidates findings from all agents
    2. Extracts top insights (cost + risk + opportunities)
    3. Calculates total business value
    4. Prioritizes recommendations
    5. Generates executive summary (2-3 pages)
    6. Creates detailed technical appendix
    7. Produces actionable roadmap
    """

    def __init__(self, workspace: Any, config: Any):
        """Initialize synthesis agent.
        
        Args:
            workspace: WorkspacePaths object
            config: EngagementConfig object
        """
        self.workspace = workspace
        self.config = config
        try:
            provider = getattr(config, 'llm_provider', 'claude')
            self.llm_client = create_llm_client(provider=provider)
        except Exception:
            # Allow agent to work without LLM in test environments
            self.llm_client = None

    def generate_executive_summary(
        self,
        topology_artifact: AnalysisArtifact,
        cost_artifact: AnalysisArtifact,
        risk_artifact: AnalysisArtifact,
    ) -> AnalysisArtifact:
        """Generate executive summary from all artifacts.
        
        Args:
            topology_artifact: System topology
            cost_artifact: Cost drivers
            risk_artifact: Risk register
            
        Returns:
            AnalysisArtifact with executive summary and appendix
        """
        # Step 1: Extract key metrics
        metrics = self._extract_metrics(topology_artifact, cost_artifact, risk_artifact)
        
        # Step 2: Identify top findings
        top_findings = self._identify_top_findings(cost_artifact, risk_artifact)
        
        # Step 3: Calculate business value
        business_value = self._calculate_business_value(cost_artifact, risk_artifact)
        
        # Step 4: Prioritize recommendations
        recommendations = self._prioritize_recommendations(cost_artifact, risk_artifact)
        
        # Step 5: Generate executive narrative with LLM
        executive_summary = self._generate_executive_narrative(
            metrics,
            top_findings,
            business_value,
            recommendations
        )
        
        # Step 6: Generate technical appendix
        technical_appendix = self._generate_technical_appendix(
            topology_artifact,
            cost_artifact,
            risk_artifact
        )
        
        # Step 7: Create action plan
        action_plan = self._generate_action_plan(recommendations)
        
        # Step 8: Create artifact
        return self._create_artifact(
            executive_summary,
            technical_appendix,
            action_plan,
            metrics,
            top_findings,
            business_value,
            recommendations
        )

    def _extract_metrics(
        self,
        topology_artifact: AnalysisArtifact,
        cost_artifact: AnalysisArtifact,
        risk_artifact: AnalysisArtifact,
    ) -> Dict[str, Any]:
        """Extract key metrics from all artifacts.
        
        Args:
            topology_artifact: System topology
            cost_artifact: Cost drivers
            risk_artifact: Risk register
            
        Returns:
            Dictionary of key metrics
        """
        topology = topology_artifact.data
        cost = cost_artifact.data
        risk = risk_artifact.data
        
        metrics = {
            # System metrics
            'total_components': topology.get('statistics', {}).get('total_nodes', 0),
            'total_dependencies': topology.get('statistics', {}).get('total_edges', 0),
            'spof_count': len(topology.get('spofs', [])),
            
            # Cost metrics
            'total_cost_ms': cost.get('summary', {}).get('total_cost_ms', 0),
            'high_impact_costs': cost.get('summary', {}).get('high_impact_count', 0),
            'queries_analyzed': cost.get('summary', {}).get('total_queries_analyzed', 0),
            
            # Risk metrics
            'total_risks': risk.get('summary', {}).get('total_risks', 0),
            'critical_risks': risk.get('summary', {}).get('critical_count', 0),
            'high_risks': risk.get('summary', {}).get('high_count', 0),
            'security_issues': risk.get('summary', {}).get('by_category', {}).get('security', 0),
        }
        
        return metrics

    def _identify_top_findings(
        self,
        cost_artifact: AnalysisArtifact,
        risk_artifact: AnalysisArtifact,
    ) -> List[Dict[str, Any]]:
        """Identify top findings across cost and risk.
        
        Selects:
        - Top 2 cost drivers
        - Top 3 risks (prioritizing CRITICAL/HIGH)
        
        Args:
            cost_artifact: Cost drivers
            risk_artifact: Risk register
            
        Returns:
            List of top findings
        """
        findings = []
        
        # Top 2 cost drivers
        cost_drivers = cost_artifact.data.get('cost_drivers', [])[:2]
        for driver in cost_drivers:
            findings.append({
                'type': 'cost',
                'title': f"Cost Driver: {driver.get('table', 'Unknown')}",
                'description': f"Query pattern executing {driver.get('execution_count', 0)} times "
                              f"with total cost of {driver.get('total_cost_ms', 0):.0f}ms",
                'impact': driver.get('impact', 'MEDIUM'),
                'recommendations': driver.get('recommendations', []),
                'details': driver
            })
        
        # Top 3 risks (CRITICAL + HIGH priority)
        risks = risk_artifact.data.get('risks', [])[:3]
        for risk in risks:
            findings.append({
                'type': 'risk',
                'title': risk.get('title', 'Unknown Risk'),
                'description': risk.get('description', ''),
                'impact': risk.get('severity', 'MEDIUM'),
                'recommendations': [risk.get('mitigation', '')],
                'details': risk
            })
        
        return findings

    def _calculate_business_value(
        self,
        cost_artifact: AnalysisArtifact,
        risk_artifact: AnalysisArtifact,
    ) -> Dict[str, Any]:
        """Calculate potential business value from optimizations.
        
        Args:
            cost_artifact: Cost drivers
            risk_artifact: Risk register
            
        Returns:
            Business value metrics
        """
        # Cost savings potential
        cost_drivers = cost_artifact.data.get('cost_drivers', [])
        
        # High impact cost drivers represent potential savings
        high_impact = [d for d in cost_drivers if d.get('impact') == 'HIGH']
        total_high_impact_cost = sum(d.get('total_cost_ms', 0) for d in high_impact)
        
        # Estimate 30-50% improvement potential for optimized queries
        estimated_savings_ms = total_high_impact_cost * 0.4  # 40% improvement
        
        # Convert to hours per day (assuming this is daily execution)
        estimated_savings_hours_per_day = (estimated_savings_ms / 1000 / 60 / 60)
        
        # Risk mitigation value (harder to quantify)
        risks = risk_artifact.data.get('risks', [])
        critical_risks = len([r for r in risks if r.get('severity') == 'CRITICAL'])
        high_risks = len([r for r in risks if r.get('severity') == 'HIGH'])
        
        return {
            'cost_savings_potential_ms': estimated_savings_ms,
            'cost_savings_potential_hours_per_day': estimated_savings_hours_per_day,
            'high_impact_cost_drivers': len(high_impact),
            'critical_risks_to_mitigate': critical_risks,
            'high_risks_to_mitigate': high_risks,
            'total_optimizable_queries': len(cost_drivers),
        }

    def _prioritize_recommendations(
        self,
        cost_artifact: AnalysisArtifact,
        risk_artifact: AnalysisArtifact,
    ) -> List[Dict[str, Any]]:
        """Prioritize recommendations by impact and effort.
        
        Args:
            cost_artifact: Cost drivers
            risk_artifact: Risk register
            
        Returns:
            Prioritized list of recommendations
        """
        recommendations = []
        
        # Extract recommendations from cost drivers
        cost_drivers = cost_artifact.data.get('cost_drivers', [])
        for i, driver in enumerate(cost_drivers[:5], 1):  # Top 5
            for rec in driver.get('recommendations', [])[:1]:  # First recommendation
                recommendations.append({
                    'priority': self._calculate_priority('cost', driver.get('impact')),
                    'category': 'performance',
                    'title': f"Optimize {driver.get('table', 'query')} performance",
                    'description': rec,
                    'impact': driver.get('impact', 'MEDIUM'),
                    'effort': 'LOW' if 'index' in rec.lower() else 'MEDIUM',
                    'source': 'cost_analysis'
                })
        
        # Extract recommendations from risks
        risks = risk_artifact.data.get('risks', [])
        for i, risk in enumerate(risks[:5], 1):  # Top 5
            mitigation = risk.get('mitigation', '')
            if mitigation:
                recommendations.append({
                    'priority': self._calculate_priority('risk', risk.get('severity')),
                    'category': risk.get('category', 'operational'),
                    'title': f"Mitigate: {risk.get('title', 'Unknown')}",
                    'description': mitigation[:200],  # First 200 chars
                    'impact': risk.get('severity', 'MEDIUM'),
                    'effort': self._estimate_effort(risk),
                    'source': 'risk_analysis'
                })
        
        # Sort by priority (higher = more important)
        recommendations = sorted(recommendations, key=lambda x: x['priority'], reverse=True)
        
        # Return top 10
        return recommendations[:10]

    def _calculate_priority(self, source: str, severity: str) -> int:
        """Calculate recommendation priority.
        
        Args:
            source: 'cost' or 'risk'
            severity: Impact level
            
        Returns:
            Priority score (higher = more important)
        """
        severity_scores = {
            'CRITICAL': 10,
            'HIGH': 7,
            'MEDIUM': 4,
            'LOW': 2
        }
        
        base_score = severity_scores.get(severity, 4)
        
        # CRITICAL risks get extra weight
        if source == 'risk' and severity == 'CRITICAL':
            base_score += 2
        
        return base_score

    def _estimate_effort(self, risk: Dict[str, Any]) -> str:
        """Estimate effort to mitigate risk.
        
        Args:
            risk: Risk dictionary
            
        Returns:
            Effort level: LOW/MEDIUM/HIGH
        """
        category = risk.get('category', '')
        
        # Heuristics based on category
        if category == 'security':
            # Security fixes are usually medium effort
            return 'MEDIUM'
        elif category == 'spof':
            # Architectural changes are high effort
            return 'HIGH'
        elif category == 'documentation':
            # Documentation is low effort
            return 'LOW'
        elif category == 'manual_ops':
            # Automation is medium effort
            return 'MEDIUM'
        else:
            return 'MEDIUM'

    def _generate_executive_narrative(
        self,
        metrics: Dict[str, Any],
        top_findings: List[Dict[str, Any]],
        business_value: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """Generate executive narrative using LLM.
        
        Args:
            metrics: Key metrics
            top_findings: Top findings
            business_value: Business value calculations
            recommendations: Prioritized recommendations
            
        Returns:
            Executive summary markdown
        """
        # Load system prompt
        prompt_path = Path(__file__).parent.parent / "prompts" / "synthesis" / "system_prompt_v1.md"
        
        if not prompt_path.exists():
            # Fallback to template-based generation
            return self._generate_template_executive_summary(
                metrics, top_findings, business_value, recommendations
            )
        
        with open(prompt_path) as f:
            system_prompt = f.read()
        
        # Prepare context
        user_message = f"""Generate an executive summary for this legacy system analysis:

CLIENT: {self.config.client_name}
ENGAGEMENT: {self.config.engagement_id}

KEY METRICS:
- System Components: {metrics['total_components']}
- Dependencies: {metrics['total_dependencies']}
- SPOFs Detected: {metrics['spof_count']}
- Total Risks: {metrics['total_risks']} ({metrics['critical_risks']} CRITICAL, {metrics['high_risks']} HIGH)
- Security Issues: {metrics['security_issues']}
- Queries Analyzed: {metrics['queries_analyzed']}

BUSINESS VALUE:
- Potential savings: {business_value['cost_savings_potential_hours_per_day']:.1f} hours/day
- High-impact optimizations: {business_value['high_impact_cost_drivers']}
- Critical risks to mitigate: {business_value['critical_risks_to_mitigate']}

TOP FINDINGS:
{self._format_findings_for_llm(top_findings[:3])}

TOP RECOMMENDATIONS:
{self._format_recommendations_for_llm(recommendations[:5])}

Generate a 2-3 page executive summary in markdown format following this structure:
1. Executive Overview (2-3 paragraphs)
2. Key Findings (3-5 bullet points)
3. Business Impact (quantified)
4. Recommended Actions (prioritized)
5. Next Steps

Use clear, executive-level language. Focus on business impact, not technical details.
"""
        
        if not self.llm_client:
            # Fallback to template if LLM not available
            return self._generate_template_executive_summary(
                metrics, top_findings, business_value, recommendations
            )
            
        try:
            response = self.llm_client.generate(
                prompt=user_message,
                system=system_prompt,
                max_tokens=2000
            )
            
            return response
            
        except Exception as e:
            # Fallback to template
            return self._generate_template_executive_summary(
                metrics, top_findings, business_value, recommendations
            )

    def _format_findings_for_llm(self, findings: List[Dict[str, Any]]) -> str:
        """Format findings for LLM prompt.
        
        Args:
            findings: List of findings
            
        Returns:
            Formatted string
        """
        lines = []
        for i, finding in enumerate(findings, 1):
            lines.append(f"{i}. [{finding['impact']}] {finding['title']}")
            lines.append(f"   {finding['description']}")
        return '\n'.join(lines)

    def _format_recommendations_for_llm(self, recommendations: List[Dict[str, Any]]) -> str:
        """Format recommendations for LLM prompt.
        
        Args:
            recommendations: List of recommendations
            
        Returns:
            Formatted string
        """
        lines = []
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. [{rec['impact']}] {rec['title']}")
            lines.append(f"   Effort: {rec['effort']}")
        return '\n'.join(lines)

    def _generate_template_executive_summary(
        self,
        metrics: Dict[str, Any],
        top_findings: List[Dict[str, Any]],
        business_value: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """Generate executive summary from template (fallback).
        
        Args:
            metrics: Key metrics
            top_findings: Top findings
            business_value: Business value
            recommendations: Recommendations
            
        Returns:
            Executive summary markdown
        """
        lines = [
            "# Executive Summary",
            "",
            f"**Client:** {self.config.client_name}",
            f"**Engagement:** {self.config.engagement_id}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## Executive Overview",
            "",
            f"We conducted a comprehensive analysis of {self.config.client_name}'s legacy systems, "
            f"examining {metrics['total_components']} components and {metrics['total_dependencies']} dependencies. "
            f"Our analysis identified {metrics['total_risks']} operational and technical risks, including "
            f"{metrics['critical_risks']} critical issues requiring immediate attention.",
            "",
            f"Through performance optimization, we identified potential savings of "
            f"{business_value['cost_savings_potential_hours_per_day']:.1f} hours per day in system execution time. "
            f"Additionally, we detected {metrics['security_issues']} security vulnerabilities and "
            f"{metrics['spof_count']} single points of failure that pose risks to operational continuity.",
            "",
            "## Key Findings",
            "",
        ]
        
        # Add top findings
        for finding in top_findings[:5]:
            impact_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(finding['impact'], '⚪')
            
            lines.append(f"- {impact_emoji} **{finding['title']}**")
            lines.append(f"  {finding['description']}")
            lines.append("")
        
        # Business impact
        lines.extend([
            "## Business Impact",
            "",
            "### Performance Optimization",
            f"- **{business_value['high_impact_cost_drivers']}** high-impact queries identified",
            f"- Estimated **{business_value['cost_savings_potential_hours_per_day']:.1f} hours/day** in savings potential",
            f"- **{business_value['total_optimizable_queries']}** total optimization opportunities",
            "",
            "### Risk Mitigation",
            f"- **{business_value['critical_risks_to_mitigate']}** critical risks requiring immediate action",
            f"- **{business_value['high_risks_to_mitigate']}** high-priority risks identified",
            f"- **{metrics['security_issues']}** security vulnerabilities detected",
            "",
            "## Recommended Actions",
            "",
            "The following recommendations are prioritized by business impact and implementation effort:",
            ""
        ])
        
        # Add prioritized recommendations
        for i, rec in enumerate(recommendations[:5], 1):
            impact_emoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }.get(rec['impact'], '⚪')
            
            effort_text = f"(Effort: {rec['effort']})"
            
            lines.append(f"### {i}. {rec['title']} {impact_emoji}")
            lines.append(f"**{effort_text}**")
            lines.append("")
            lines.append(rec['description'])
            lines.append("")
        
        # Next steps
        lines.extend([
            "## Next Steps",
            "",
            "We recommend the following phased approach:",
            "",
            "**Phase 1: Critical Issues (Immediate)**",
            "- Address all CRITICAL risks identified in the risk register",
            "- Implement security fixes for hardcoded credentials",
            "- Begin SPOF mitigation for highest-risk components",
            "",
            "**Phase 2: Performance Optimization (1-2 months)**",
            "- Implement high-impact query optimizations",
            "- Add missing database indexes",
            "- Optimize batch job performance",
            "",
            "**Phase 3: Operational Excellence (3-6 months)**",
            "- Automate manual operations",
            "- Document tribal knowledge",
            "- Implement monitoring and alerting",
            "",
            "---",
            "",
            f"*For detailed technical findings, please refer to the Technical Appendix.*"
        ])
        
        return '\n'.join(lines)

    def _generate_technical_appendix(
        self,
        topology_artifact: AnalysisArtifact,
        cost_artifact: AnalysisArtifact,
        risk_artifact: AnalysisArtifact,
    ) -> str:
        """Generate detailed technical appendix.
        
        Args:
            topology_artifact: System topology
            cost_artifact: Cost drivers
            risk_artifact: Risk register
            
        Returns:
            Technical appendix markdown
        """
        lines = [
            "# Technical Appendix",
            "",
            f"**Client:** {self.config.client_name}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
            "## 1. System Architecture Analysis",
            "",
        ]
        
        # Topology summary
        topology = topology_artifact.data
        stats = topology.get('statistics', {})
        
        lines.extend([
            "### System Topology",
            "",
            f"- **Total Components:** {stats.get('total_nodes', 0)}",
            f"- **Total Dependencies:** {stats.get('total_edges', 0)}",
            f"- **Graph Density:** {stats.get('graph_density', 0):.3f}",
            f"- **Average Degree:** {stats.get('avg_degree', 0):.2f}",
            "",
        ])
        
        # SPOFs
        spofs = topology.get('spofs', [])
        if spofs:
            lines.extend([
                "### Single Points of Failure",
                "",
            ])
            
            for spof in spofs[:5]:
                lines.extend([
                    f"**{spof.get('node_name')}** ({spof.get('node_type')})",
                    f"- Risk Level: {spof.get('risk_level').upper()}",
                    f"- Centrality: {spof.get('centrality', 0):.3f}",
                    f"- Dependencies: {len(spof.get('dependent_components', []))}",
                    "",
                ])
        
        # Cost analysis
        lines.extend([
            "---",
            "",
            "## 2. Performance & Cost Analysis",
            "",
        ])
        
        cost = cost_artifact.data
        cost_summary = cost.get('summary', {})
        
        lines.extend([
            "### Summary Statistics",
            "",
            f"- **Queries Analyzed:** {cost_summary.get('total_queries_analyzed', 0):,}",
            f"- **Unique Query Patterns:** {cost_summary.get('unique_query_patterns', 0)}",
            f"- **Total Cost:** {cost_summary.get('total_cost_ms', 0):,.0f}ms",
            f"- **High Impact:** {cost_summary.get('high_impact_count', 0)}",
            f"- **Medium Impact:** {cost_summary.get('medium_impact_count', 0)}",
            "",
            "### Top Cost Drivers",
            "",
        ])
        
        cost_drivers = cost.get('cost_drivers', [])
        for i, driver in enumerate(cost_drivers[:10], 1):
            lines.extend([
                f"#### {i}. {driver.get('table', 'Unknown')} [{driver.get('impact')}]",
                "",
                f"- **Execution Count:** {driver.get('execution_count', 0):,}",
                f"- **Avg Duration:** {driver.get('avg_duration_ms', 0):.2f}ms",
                f"- **Total Cost:** {driver.get('total_cost_ms', 0):,.0f}ms",
                "",
                "**Query Pattern:**",
                f"```sql",
                driver.get('query_pattern', '')[:200],
                f"```",
                "",
            ])
            
            if driver.get('missing_indexes'):
                lines.extend([
                    "**Missing Indexes:**",
                    *[f"- {idx}" for idx in driver['missing_indexes']],
                    "",
                ])
        
        # Risk analysis
        lines.extend([
            "---",
            "",
            "## 3. Risk Assessment",
            "",
        ])
        
        risk = risk_artifact.data
        risk_summary = risk.get('summary', {})
        
        lines.extend([
            "### Risk Summary",
            "",
            f"- **Total Risks:** {risk_summary.get('total_risks', 0)}",
            f"- **Critical:** {risk_summary.get('critical_count', 0)}",
            f"- **High:** {risk_summary.get('high_count', 0)}",
            f"- **Medium:** {risk_summary.get('medium_count', 0)}",
            f"- **Low:** {risk_summary.get('low_count', 0)}",
            "",
            "### Risk by Category",
            "",
        ])
        
        by_category = risk_summary.get('by_category', {})
        for category, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- **{category.replace('_', ' ').title()}:** {count}")
        
        lines.extend([
            "",
            "### Critical & High Risks",
            "",
        ])
        
        risks = risk.get('risks', [])
        critical_and_high = [r for r in risks if r.get('severity') in ['CRITICAL', 'HIGH']]
        
        for i, risk_item in enumerate(critical_and_high[:10], 1):
            lines.extend([
                f"#### {i}. {risk_item.get('title')} [{risk_item.get('severity')}]",
                "",
                f"**Category:** {risk_item.get('category')}",
                f"**Confidence:** {risk_item.get('confidence')}",
                "",
                f"{risk_item.get('description', '')}",
                "",
            ])
            
            if risk_item.get('mitigation'):
                lines.extend([
                    "**Mitigation:**",
                    risk_item['mitigation'][:300],
                    "",
                ])
        
        lines.extend([
            "---",
            "",
            "*End of Technical Appendix*"
        ])
        
        return '\n'.join(lines)

    def _generate_action_plan(
        self,
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Generate actionable roadmap.
        
        Args:
            recommendations: Prioritized recommendations
            
        Returns:
            Action plan markdown
        """
        lines = [
            "# Action Plan",
            "",
            f"**Client:** {self.config.client_name}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## Phased Implementation Roadmap",
            "",
        ]
        
        # Group by effort
        by_effort = defaultdict(list)
        for rec in recommendations:
            by_effort[rec['effort']].append(rec)
        
        # Phase 1: Quick wins (LOW effort)
        if by_effort['LOW']:
            lines.extend([
                "### Phase 1: Quick Wins (1-2 weeks)",
                "",
                "These are high-impact, low-effort items that can be implemented quickly:",
                "",
            ])
            
            for i, rec in enumerate(by_effort['LOW'][:5], 1):
                lines.extend([
                    f"{i}. **{rec['title']}**",
                    f"   - Impact: {rec['impact']}",
                    f"   - Category: {rec['category']}",
                    "",
                ])
        
        # Phase 2: Core improvements (MEDIUM effort)
        if by_effort['MEDIUM']:
            lines.extend([
                "### Phase 2: Core Improvements (1-3 months)",
                "",
                "These require more effort but provide significant value:",
                "",
            ])
            
            for i, rec in enumerate(by_effort['MEDIUM'][:5], 1):
                lines.extend([
                    f"{i}. **{rec['title']}**",
                    f"   - Impact: {rec['impact']}",
                    f"   - Category: {rec['category']}",
                    "",
                ])
        
        # Phase 3: Strategic initiatives (HIGH effort)
        if by_effort['HIGH']:
            lines.extend([
                "### Phase 3: Strategic Initiatives (3-6 months)",
                "",
                "These are larger architectural changes requiring careful planning:",
                "",
            ])
            
            for i, rec in enumerate(by_effort['HIGH'][:3], 1):
                lines.extend([
                    f"{i}. **{rec['title']}**",
                    f"   - Impact: {rec['impact']}",
                    f"   - Category: {rec['category']}",
                    "",
                ])
        
        lines.extend([
            "## Success Metrics",
            "",
            "Track the following KPIs to measure progress:",
            "",
            "- Query performance improvements (target: 30-50% reduction in high-impact queries)",
            "- Critical risk mitigation (target: 100% within 3 months)",
            "- Security vulnerability closure (target: 100% within 1 month)",
            "- SPOF reduction (target: 50% within 6 months)",
            "- Documentation coverage (target: >50% within 6 months)",
            "",
            "---",
            "",
            "*For detailed implementation guidance, consult with your technical team.*"
        ])
        
        return '\n'.join(lines)

    def _create_artifact(
        self,
        executive_summary: str,
        technical_appendix: str,
        action_plan: str,
        metrics: Dict[str, Any],
        top_findings: List[Dict[str, Any]],
        business_value: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> AnalysisArtifact:
        """Create synthesis artifact.
        
        Args:
            executive_summary: Executive summary markdown
            technical_appendix: Technical appendix markdown
            action_plan: Action plan markdown
            metrics: Key metrics
            top_findings: Top findings
            business_value: Business value
            recommendations: Recommendations
            
        Returns:
            AnalysisArtifact
        """
        data = {
            'executive_summary': executive_summary,
            'technical_appendix': technical_appendix,
            'action_plan': action_plan,
            'metrics': metrics,
            'top_findings': top_findings,
            'business_value': business_value,
            'recommendations': recommendations,
        }
        
        sources = [
            SourceReference(
                type='topology',
                path='topology.json',
                timestamp=datetime.now()
            ),
            SourceReference(
                type='cost_drivers',
                path='cost_drivers.json',
                timestamp=datetime.now()
            ),
            SourceReference(
                type='risk_register',
                path='risk_register.json',
                timestamp=datetime.now()
            )
        ]
        
        artifact_metrics = {
            'total_findings': len(top_findings),
            'total_recommendations': len(recommendations),
            'critical_risks': metrics['critical_risks'],
            'potential_savings_hours': business_value['cost_savings_potential_hours_per_day'],
        }
        
        artifact = AnalysisArtifact(
            artifact_type='synthesis',
            engagement_id=self.config.engagement_id,
            data=data,
            sources=sources,
            metrics=artifact_metrics,
            confidence=ConfidenceLevel.HIGH  # High confidence from consolidated analysis
        )
        
        # Save artifacts
        self._save_artifacts(
            artifact,
            executive_summary,
            technical_appendix,
            action_plan
        )
        
        return artifact

    def _save_artifacts(
        self,
        artifact: AnalysisArtifact,
        executive_summary: str,
        technical_appendix: str,
        action_plan: str,
    ) -> None:
        """Save synthesis artifacts.
        
        Args:
            artifact: Main artifact
            executive_summary: Executive summary
            technical_appendix: Technical appendix
            action_plan: Action plan
        """
        # Save main artifact
        artifact_path = self.workspace.artifacts / "synthesis.json"
        with open(artifact_path, 'w') as f:
            json.dump(artifact.model_dump(mode='json'), f, indent=2, default=str)
        
        # Save executive summary
        exec_path = self.workspace.artifacts / "executive_summary.md"
        with open(exec_path, 'w') as f:
            f.write(executive_summary)
        
        # Save technical appendix
        tech_path = self.workspace.artifacts / "technical_appendix.md"
        with open(tech_path, 'w') as f:
            f.write(technical_appendix)
        
        # Save action plan
        action_path = self.workspace.artifacts / "action_plan.md"
        with open(action_path, 'w') as f:
            f.write(action_plan)
        
        # Save sources
        sources_path = self.workspace.artifacts / "synthesis_sources.json"
        with open(sources_path, 'w') as f:
            json.dump(
                [s.model_dump(mode='json') for s in artifact.sources],
                f,
                indent=2,
                default=str
            )
        
        # Save metrics
        metrics_path = self.workspace.artifacts / "synthesis_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(artifact.metrics, f, indent=2)