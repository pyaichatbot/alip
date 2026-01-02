"""RiskAnalysisAgent - Identify operational and technical risks.

This agent analyzes legacy systems to identify various types of risks:
- Single Points of Failure (SPOFs)
- Tribal knowledge dependencies
- Manual operations
- Security vulnerabilities
- Undocumented components

Risk Severity Classification:
    CRITICAL: Immediate threat to operations
    HIGH: Significant risk requiring attention
    MEDIUM: Moderate risk, should be addressed
    LOW: Minor risk, can be deferred

Risk Categories:
    - spof: Single points of failure
    - tribal_knowledge: Undocumented expertise
    - manual_ops: Manual processes
    - security: Security vulnerabilities
    - documentation: Missing/outdated docs
    - operational: Operational issues
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.models import AnalysisArtifact, Risk, SourceReference, ConfidenceLevel
from core.llm.client import create_llm_client


class RiskAnalysisAgent:
    """Agent for identifying system risks and mitigation strategies.
    
    This agent:
    1. Detects SPOFs from topology analysis
    2. Identifies tribal knowledge patterns in docs
    3. Finds manual operations in runbooks
    4. Scans code for security issues
    5. Calculates severity × likelihood
    6. Generates mitigation recommendations
    """

    # Tribal knowledge patterns
    TRIBAL_PATTERNS = [
        r'contact\s+(\w+)',
        r'ask\s+(\w+)',
        r'only\s+(\w+)\s+knows',
        r'(\w+)\s+is\s+the\s+only\s+one',
        r'reach\s+out\s+to\s+(\w+)',
        r'see\s+(\w+)\s+for',
    ]

    # Security vulnerability patterns
    SECURITY_PATTERNS = {
        'hardcoded_password': [
            r'password\s*=\s*["\']([^"\']+)["\']',
            r'passwd\s*=\s*["\']([^"\']+)["\']',
            r'pwd\s*=\s*["\']([^"\']+)["\']',
        ],
        'api_key': [
            r'api_key\s*=\s*["\']([^"\']+)["\']',
            r'api_secret\s*=\s*["\']([^"\']+)["\']',
            r'secret_key\s*=\s*["\']([^"\']+)["\']',
        ],
        'sql_injection': [
            r'execute\s*\(\s*["\'].*%s.*["\']',
            r'query\s*\(\s*["\'].*\+.*["\']',
            r'\.format\s*\(.*sql.*\)',
        ],
        'insecure_connection': [
            r'http://(?!localhost|127\.0\.0\.1)',
            r'verify\s*=\s*False',
            r'ssl_verify\s*=\s*False',
        ]
    }

    # Manual operation patterns
    MANUAL_PATTERNS = [
        r'manually\s+(\w+)',
        r'run\s+this\s+command',
        r'execute\s+the\s+following',
        r'ssh\s+into',
        r'log\s+into',
    ]

    def __init__(self, workspace: Any, config: Any):
        """Initialize risk analysis agent.
        
        Args:
            workspace: WorkspacePaths object
            config: EngagementConfig object
        """
        self.workspace = workspace
        self.config = config
        try:
            self.llm_client = create_llm_client()
        except Exception:
            # Allow agent to work without LLM in test environments
            self.llm_client = None

    def analyze_risks(
        self,
        repo_artifact: AnalysisArtifact,
        db_artifact: AnalysisArtifact,
        docs_artifact: AnalysisArtifact,
        topology_artifact: AnalysisArtifact,
    ) -> AnalysisArtifact:
        """Analyze system for operational and technical risks.
        
        Args:
            repo_artifact: Repository inventory
            db_artifact: Database schema
            docs_artifact: Documentation
            topology_artifact: System topology
            
        Returns:
            AnalysisArtifact with risk register
        """
        risks: List[Dict[str, Any]] = []
        
        # 1. Detect SPOFs from topology
        spof_risks = self._detect_spofs(topology_artifact)
        risks.extend(spof_risks)
        
        # 2. Detect tribal knowledge from docs
        tribal_risks = self._detect_tribal_knowledge(docs_artifact)
        risks.extend(tribal_risks)
        
        # 3. Detect manual operations from docs
        manual_risks = self._detect_manual_operations(docs_artifact)
        risks.extend(manual_risks)
        
        # 4. Detect security issues from code
        security_risks = self._detect_security_issues(repo_artifact)
        risks.extend(security_risks)
        
        # 5. Detect documentation gaps
        doc_risks = self._detect_documentation_gaps(repo_artifact, docs_artifact)
        risks.extend(doc_risks)
        
        # 6. Detect database risks
        db_risks = self._detect_database_risks(db_artifact, topology_artifact)
        risks.extend(db_risks)
        
        # 7. Calculate risk scores
        risks = self._calculate_risk_scores(risks)
        
        # 8. Use LLM for analysis (top 5 risks)
        risks = self._analyze_with_llm(risks[:5])
        
        # 9. Rank by severity and return top 15
        risks = self._rank_risks(risks)[:15]
        
        # 10. Create artifact
        return self._create_artifact(risks)

    def _detect_spofs(self, topology_artifact: AnalysisArtifact) -> List[Dict[str, Any]]:
        """Detect single points of failure from topology.
        
        Analyzes:
        - Components with no redundancy
        - High betweenness centrality (critical paths)
        - Single dependencies
        
        Args:
            topology_artifact: System topology
            
        Returns:
            List of SPOF risk dictionaries
        """
        risks = []
        topology = topology_artifact.data
        
        # Get SPOFs already identified by TopologyAgent
        spofs = topology.get('spofs', [])
        
        for spof in spofs:
            node_name = spof.get('node_name', 'Unknown')
            node_type = spof.get('node_type', 'unknown')
            risk_level = spof.get('risk_level', 'medium')
            
            # Map risk level to severity
            severity_map = {
                'critical': 'CRITICAL',
                'high': 'HIGH',
                'medium': 'MEDIUM',
                'low': 'LOW'
            }
            severity = severity_map.get(risk_level, 'MEDIUM')
            
            # Create risk
            risk = {
                'title': f'SPOF: {node_name}',
                'description': f'Component "{node_name}" is a single point of failure. '
                              f'It has high centrality ({spof.get("centrality", 0):.3f}) '
                              f'and is critical to system operation.',
                'severity': severity,
                'category': 'spof',
                'evidence': [
                    {
                        'type': 'topology',
                        'path': 'topology.json',
                        'timestamp': datetime.now().isoformat(),
                        'details': f'Betweenness centrality: {spof.get("centrality", 0):.3f}'
                    }
                ],
                'confidence': 'high',
                'affected_components': spof.get('dependent_components', []),
                'mitigation': None  # Will be filled by LLM
            }
            
            risks.append(risk)
        
        return risks

    def _detect_tribal_knowledge(
        self,
        docs_artifact: AnalysisArtifact
    ) -> List[Dict[str, Any]]:
        """Detect tribal knowledge patterns in documentation.
        
        Searches for:
        - "Contact [person]"
        - "Ask [person]"
        - "Only [person] knows"
        - Outdated documentation
        
        Args:
            docs_artifact: Documentation artifact
            
        Returns:
            List of tribal knowledge risk dictionaries
        """
        risks = []
        docs = docs_artifact.data.get('documents', [])
        
        name_mentions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        for doc in docs:
            content = doc.get('content', '') or doc.get('text_content', '')
            file_path = doc.get('path', 'unknown')
            
            # Search for tribal knowledge patterns
            for pattern in self.TRIBAL_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    if match.groups():
                        person_name = match.group(1)
                        context = self._extract_context(content, match.start(), 100)
                        
                        name_mentions[person_name.lower()].append({
                            'file': file_path,
                            'context': context,
                            'pattern': pattern
                        })
        
        # Create risks for people mentioned multiple times
        for person, mentions in name_mentions.items():
            if len(mentions) >= 2:  # Mentioned 2+ times
                files = list(set(m['file'] for m in mentions))
                
                risk = {
                    'title': f'Tribal Knowledge: {person.title()}',
                    'description': f'Person "{person.title()}" is mentioned {len(mentions)} times '
                                  f'across {len(files)} document(s) as a knowledge source. '
                                  f'This indicates tribal knowledge dependency.',
                    'severity': 'HIGH' if len(mentions) >= 5 else 'MEDIUM',
                    'category': 'tribal_knowledge',
                    'evidence': [
                        {
                            'type': 'document',
                            'path': m['file'],
                            'timestamp': datetime.now().isoformat(),
                            'details': m['context']
                        }
                        for m in mentions[:3]  # Max 3 examples
                    ],
                    'confidence': 'medium',
                    'person_name': person.title(),
                    'mention_count': len(mentions),
                    'affected_files': files,
                    'mitigation': f'Document expertise of {person.title()} in formal documentation'
                }
                
                risks.append(risk)
        
        return risks

    def _detect_manual_operations(
        self,
        docs_artifact: AnalysisArtifact
    ) -> List[Dict[str, Any]]:
        """Detect manual operations in documentation.
        
        Searches for:
        - "Manually run..."
        - "SSH into..."
        - "Execute command..."
        
        Args:
            docs_artifact: Documentation artifact
            
        Returns:
            List of manual operation risk dictionaries
        """
        risks = []
        docs = docs_artifact.data.get('documents', [])
        
        manual_ops: List[Dict[str, Any]] = []
        
        for doc in docs:
            content = doc.get('content', '') or doc.get('text_content', '')
            file_path = doc.get('path', 'unknown')
            
            for pattern in self.MANUAL_PATTERNS:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    context = self._extract_context(content, match.start(), 150)
                    
                    manual_ops.append({
                        'file': file_path,
                        'context': context,
                        'pattern': match.group(0)
                    })
        
        # Group by file
        ops_by_file: Dict[str, List[Dict]] = defaultdict(list)
        for op in manual_ops:
            ops_by_file[op['file']].append(op)
        
        # Create risks for files with multiple manual operations
        for file_path, ops in ops_by_file.items():
            if len(ops) >= 2:
                risk = {
                    'title': f'Manual Operations in {Path(file_path).name}',
                    'description': f'Document contains {len(ops)} manual operation(s). '
                                  f'Manual processes are error-prone and not scalable.',
                    'severity': 'MEDIUM',
                    'category': 'manual_ops',
                    'evidence': [
                        {
                            'type': 'document',
                            'path': file_path,
                            'timestamp': datetime.now().isoformat(),
                            'details': op['context']
                        }
                        for op in ops[:3]
                    ],
                    'confidence': 'medium',
                    'operation_count': len(ops),
                    'mitigation': 'Automate these operations with scripts or CI/CD'
                }
                
                risks.append(risk)
        
        return risks

    def _detect_security_issues(
        self,
        repo_artifact: AnalysisArtifact
    ) -> List[Dict[str, Any]]:
        """Detect security vulnerabilities in code.
        
        Searches for:
        - Hardcoded passwords
        - API keys in code
        - SQL injection patterns
        - Insecure connections
        
        Args:
            repo_artifact: Repository artifact
            
        Returns:
            List of security risk dictionaries
        """
        risks = []
        
        # Try to get files from artifact (if available)
        files = repo_artifact.data.get('files', [])
        
        # If no files in artifact, try to read from repository path
        if not files:
            repo_path = repo_artifact.data.get('path', '')
            if repo_path and Path(repo_path).exists():
                # Scan repository directory for code files
                repo_dir = Path(repo_path)
                for file_path in repo_dir.rglob('*'):
                    if not file_path.is_file():
                        continue
                    if not self._is_code_file(str(file_path)):
                        continue
                    # Skip large files and common exclusions
                    if file_path.stat().st_size > 1_000_000:  # > 1MB
                        continue
                    if any(skip in str(file_path) for skip in ['.git', '__pycache__', 'node_modules', '.venv']):
                        continue
                    
                    files.append({'path': str(file_path), 'content': ''})
        
        for file_info in files:
            file_path = file_info.get('path', '')
            
            # Skip non-code files
            if not self._is_code_file(file_path):
                continue
            
            # Read file content (if available)
            content = file_info.get('content', '')
            if not content:
                # Try to read from disk
                full_path = Path(file_path)
                if full_path.exists() and full_path.stat().st_size < 1_000_000:  # < 1MB
                    try:
                        content = full_path.read_text(encoding='utf-8', errors='ignore')
                    except Exception:
                        continue
            
            if not content:
                continue
            
            # Check each security pattern
            for issue_type, patterns in self.SECURITY_PATTERNS.items():
                for pattern in patterns:
                    matches = list(re.finditer(pattern, content, re.IGNORECASE))
                    
                    if matches:
                        # Group multiple matches in same file
                        context = self._extract_context(content, matches[0].start(), 80)
                        
                        severity_map = {
                            'hardcoded_password': 'CRITICAL',
                            'api_key': 'CRITICAL',
                            'sql_injection': 'HIGH',
                            'insecure_connection': 'MEDIUM'
                        }
                        
                        risk = {
                            'title': f'Security: {issue_type.replace("_", " ").title()} in {Path(file_path).name}',
                            'description': f'Found {len(matches)} instance(s) of {issue_type.replace("_", " ")} '
                                          f'in {file_path}. This is a security vulnerability.',
                            'severity': severity_map.get(issue_type, 'HIGH'),
                            'category': 'security',
                            'evidence': [
                                {
                                    'type': 'code',
                                    'path': file_path,
                                    'timestamp': datetime.now().isoformat(),
                                    'details': context
                                }
                            ],
                            'confidence': 'high',
                            'issue_type': issue_type,
                            'occurrence_count': len(matches),
                            'mitigation': self._get_security_mitigation(issue_type)
                        }
                        
                        risks.append(risk)
                        break  # One risk per issue type per file
        
        return risks

    def _detect_documentation_gaps(
        self,
        repo_artifact: AnalysisArtifact,
        docs_artifact: AnalysisArtifact
    ) -> List[Dict[str, Any]]:
        """Detect documentation gaps.
        
        Checks for:
        - Code files without corresponding documentation
        - Large files without comments
        
        Args:
            repo_artifact: Repository artifact
            docs_artifact: Documentation artifact
            
        Returns:
            List of documentation risk dictionaries
        """
        risks = []
        
        files = repo_artifact.data.get('files', [])
        docs = docs_artifact.data.get('documents', [])
        
        # Count code files
        code_files = [f for f in files if self._is_code_file(f.get('path', ''))]
        
        # Count documentation files
        doc_count = len(docs)
        
        # Calculate ratio
        if len(code_files) > 0:
            doc_ratio = doc_count / len(code_files)
            
            if doc_ratio < 0.1:  # Less than 10% documentation coverage
                risk = {
                    'title': 'Insufficient Documentation',
                    'description': f'Found only {doc_count} documentation file(s) for {len(code_files)} code files. '
                                  f'Documentation coverage is {doc_ratio:.1%}. '
                                  f'This makes the system harder to maintain and onboard new team members.',
                    'severity': 'HIGH',
                    'category': 'documentation',
                    'evidence': [
                        {
                            'type': 'repository',
                            'path': 'repository.json',
                            'timestamp': datetime.now().isoformat(),
                            'details': f'{len(code_files)} code files, {doc_count} docs'
                        }
                    ],
                    'confidence': 'high',
                    'code_file_count': len(code_files),
                    'doc_file_count': doc_count,
                    'doc_ratio': doc_ratio,
                    'mitigation': 'Create README files, architecture docs, and inline code comments'
                }
                
                risks.append(risk)
        
        return risks

    def _detect_database_risks(
        self,
        db_artifact: AnalysisArtifact,
        topology_artifact: AnalysisArtifact
    ) -> List[Dict[str, Any]]:
        """Detect database-related risks.
        
        Checks for:
        - Tables without indexes
        - Foreign keys without indexes
        - Large tables
        
        Args:
            db_artifact: Database schema artifact
            topology_artifact: System topology
            
        Returns:
            List of database risk dictionaries
        """
        risks = []
        schema = db_artifact.data
        tables = schema.get('tables', [])
        all_indexes = schema.get('indexes', [])
        
        # Create a set of tables that have indexes
        indexed_tables = set()
        for index in all_indexes:
            table_name = index.get('table', '')
            if table_name:
                indexed_tables.add(table_name.lower())
        
        # Check for tables without indexes
        unindexed_tables = []
        for table in tables:
            table_name = table.get('name', '')
            # Check if table has indexes (either in table.indexes or in global indexes list)
            table_indexes = table.get('indexes', [])
            if not table_indexes and table_name.lower() not in indexed_tables:
                unindexed_tables.append(table_name)
        
        if unindexed_tables:
            risk = {
                'title': 'Tables Without Indexes',
                'description': f'Found {len(unindexed_tables)} table(s) without any indexes: '
                              f'{", ".join(unindexed_tables[:5])}. '
                              f'This can lead to slow query performance.',
                'severity': 'MEDIUM',
                'category': 'operational',
                'evidence': [
                    {
                        'type': 'database',
                        'path': 'database.json',
                        'timestamp': datetime.now().isoformat(),
                        'details': f'Unindexed tables: {", ".join(unindexed_tables)}'
                    }
                ],
                'confidence': 'high',
                'table_count': len(unindexed_tables),
                'table_names': unindexed_tables,
                'mitigation': 'Add appropriate indexes based on query patterns'
            }
            
            risks.append(risk)
        
        return risks

    def _calculate_risk_scores(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate numerical risk scores for ranking.
        
        Score = severity_weight × confidence_weight
        
        Args:
            risks: List of risk dictionaries
            
        Returns:
            Updated risks with risk_score field
        """
        severity_weights = {
            'CRITICAL': 10,
            'HIGH': 7,
            'MEDIUM': 4,
            'LOW': 2
        }
        
        confidence_weights = {
            'high': 1.0,
            'medium': 0.7,
            'low': 0.4
        }
        
        for risk in risks:
            severity = risk.get('severity', 'MEDIUM')
            confidence = risk.get('confidence', 'medium')
            
            sev_weight = severity_weights.get(severity, 4)
            conf_weight = confidence_weights.get(confidence, 0.7)
            
            risk['risk_score'] = sev_weight * conf_weight
        
        return risks

    def _analyze_with_llm(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to analyze risks and enhance recommendations.
        
        Args:
            risks: Top risks to analyze
            
        Returns:
            Updated risks with LLM-generated insights
        """
        if not risks:
            return risks
        
        # Load system prompt
        prompt_path = Path(__file__).parent.parent / "prompts" / "risk_analysis" / "system_prompt_v1.md"
        
        if not prompt_path.exists():
            return risks
        
        with open(prompt_path) as f:
            system_prompt = f.read()
        
        # Analyze each risk
        if not self.llm_client:
            return risks
            
        for risk in risks[:5]:  # Top 5 only
            try:
                user_message = f"""Analyze this risk:

Title: {risk['title']}
Description: {risk['description']}
Severity: {risk['severity']}
Category: {risk['category']}

Provide:
1. Detailed impact analysis
2. Specific mitigation steps
3. Estimated effort to remediate"""
                
                response = self.llm_client.generate(
                    prompt=user_message,
                    system=system_prompt,
                    max_tokens=500
                )
                
                # Update mitigation if better
                if risk.get('mitigation'):
                    risk['mitigation'] += f'\n\nLLM Analysis: {response}'
                else:
                    risk['mitigation'] = response
                
            except Exception as e:
                # Continue on error
                if not risk.get('mitigation'):
                    risk['mitigation'] = 'Mitigation analysis unavailable'
        
        return risks

    def _rank_risks(self, risks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank risks by score and severity.
        
        Args:
            risks: List of risks
            
        Returns:
            Sorted risks (highest priority first)
        """
        # Sort by risk_score (descending), then severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        
        return sorted(
            risks,
            key=lambda r: (
                -r.get('risk_score', 0),
                severity_order.get(r.get('severity', 'MEDIUM'), 2)
            )
        )

    def _extract_context(self, text: str, position: int, length: int) -> str:
        """Extract context around a position in text.
        
        Args:
            text: Full text
            position: Match position
            length: Context length
            
        Returns:
            Context string
        """
        start = max(0, position - length // 2)
        end = min(len(text), position + length // 2)
        
        context = text[start:end].strip()
        
        if start > 0:
            context = '...' + context
        if end < len(text):
            context = context + '...'
        
        return context

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file.
        
        Args:
            file_path: File path
            
        Returns:
            True if code file
        """
        code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs',
            '.go', '.rb', '.php', '.scala', '.kt', '.swift',
            '.rs', '.sql'
        }
        
        return Path(file_path).suffix.lower() in code_extensions

    def _get_security_mitigation(self, issue_type: str) -> str:
        """Get mitigation advice for security issue.
        
        Args:
            issue_type: Type of security issue
            
        Returns:
            Mitigation advice
        """
        mitigations = {
            'hardcoded_password': 'Move credentials to environment variables or secrets manager',
            'api_key': 'Store API keys in environment variables or secrets manager',
            'sql_injection': 'Use parameterized queries or ORM with proper escaping',
            'insecure_connection': 'Enable SSL/TLS verification and use HTTPS'
        }
        
        return mitigations.get(issue_type, 'Review and remediate security issue')

    def _create_artifact(self, risks: List[Dict[str, Any]]) -> AnalysisArtifact:
        """Create risk analysis artifact.
        
        Args:
            risks: Risk list
            
        Returns:
            AnalysisArtifact
        """
        # Calculate summary stats
        total_risks = len(risks)
        critical_count = len([r for r in risks if r['severity'] == 'CRITICAL'])
        high_count = len([r for r in risks if r['severity'] == 'HIGH'])
        medium_count = len([r for r in risks if r['severity'] == 'MEDIUM'])
        low_count = len([r for r in risks if r['severity'] == 'LOW'])
        
        # Group by category
        by_category = defaultdict(int)
        for risk in risks:
            by_category[risk['category']] += 1
        
        data = {
            'risks': risks,
            'summary': {
                'total_risks': total_risks,
                'critical_count': critical_count,
                'high_count': high_count,
                'medium_count': medium_count,
                'low_count': low_count,
                'by_category': dict(by_category)
            }
        }
        
        # Create sources
        sources = [
            SourceReference(
                type='topology',
                path='topology.json',
                timestamp=datetime.now()
            ),
            SourceReference(
                type='documents',
                path='documents.json',
                timestamp=datetime.now()
            ),
            SourceReference(
                type='repository',
                path='repository.json',
                timestamp=datetime.now()
            )
        ]
        
        # Create metrics
        metrics = {
            'risk_count': total_risks,
            'critical_count': critical_count,
            'high_count': high_count
        }
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type='risk_register',
            engagement_id=self.config.engagement_id,
            data=data,
            sources=sources,
            metrics=metrics,
            confidence=ConfidenceLevel.HIGH
        )
        
        # Save artifacts
        self._save_artifacts(artifact, risks)
        
        return artifact

    def _save_artifacts(
        self,
        artifact: AnalysisArtifact,
        risks: List[Dict[str, Any]]
    ) -> None:
        """Save risk analysis artifacts.
        
        Args:
            artifact: Main artifact
            risks: Risk list
        """
        # Save main artifact
        artifact_path = self.workspace.artifacts / "risk_register.json"
        with open(artifact_path, 'w') as f:
            json.dump(artifact.model_dump(mode='json'), f, indent=2, default=str)
        
        # Save markdown summary
        md_path = self.workspace.artifacts / "risk_register.md"
        self._generate_markdown(risks, md_path)
        
        # Save sources
        sources_path = self.workspace.artifacts / "risk_register_sources.json"
        with open(sources_path, 'w') as f:
            json.dump(
                [s.model_dump(mode='json') for s in artifact.sources],
                f,
                indent=2,
                default=str
            )
        
        # Save metrics
        metrics_path = self.workspace.artifacts / "risk_register_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(artifact.metrics, f, indent=2)

    def _generate_markdown(
        self,
        risks: List[Dict[str, Any]],
        output_path: Path
    ) -> None:
        """Generate human-readable markdown report.
        
        Args:
            risks: Risk list
            output_path: Output path
        """
        lines = [
            "# Risk Analysis Report",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Engagement:** {self.config.client_name}",
            "",
            "## Executive Summary",
            "",
            f"- **Total Risks Identified:** {len(risks)}",
        ]
        
        if risks:
            critical = len([r for r in risks if r['severity'] == 'CRITICAL'])
            high = len([r for r in risks if r['severity'] == 'HIGH'])
            medium = len([r for r in risks if r['severity'] == 'MEDIUM'])
            low = len([r for r in risks if r['severity'] == 'LOW'])
            
            lines.extend([
                f"- **Critical:** {critical}",
                f"- **High:** {high}",
                f"- **Medium:** {medium}",
                f"- **Low:** {low}",
                "",
                "## Risk Register",
                ""
            ])
            
            for i, risk in enumerate(risks, 1):
                lines.extend([
                    f"### {i}. {risk['title']} [{risk['severity']}]",
                    "",
                    f"**Category:** {risk['category']}",
                    f"**Confidence:** {risk['confidence']}",
                    "",
                    f"**Description:**",
                    risk['description'],
                    "",
                ])
                
                if risk.get('mitigation'):
                    lines.extend([
                        f"**Mitigation:**",
                        risk['mitigation'],
                        "",
                    ])
                
                if risk.get('evidence'):
                    lines.extend([
                        f"**Evidence:**",
                        *[f"- {ev.get('type', 'unknown')}: {ev.get('details', '')[:100]}" 
                          for ev in risk['evidence'][:2]],
                        "",
                    ])
        else:
            lines.extend([
                "",
                "*No significant risks identified.*",
                ""
            ])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))