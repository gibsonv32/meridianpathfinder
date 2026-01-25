"""Enhanced LLM Intelligence Module for MERIDIAN

Provides:
- Few-shot learning from successful examples
- Conversation memory across interactions
- Dynamic prompt optimization
- Domain-specific knowledge injection
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque
import hashlib

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """Single turn in conversation history"""
    timestamp: datetime
    mode: str
    prompt: str
    response: str
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FewShotExample:
    """Example for few-shot learning"""
    mode: str
    input_context: Dict[str, Any]
    prompt: str
    response: str
    quality_score: float  # 0-1, higher is better
    artifact_id: Optional[str] = None
    
    def to_prompt_text(self) -> str:
        """Convert to text for inclusion in prompts"""
        return f"""
Example Input:
{json.dumps(self.input_context, indent=2)}

Example Output:
{self.response}

Quality: {self.quality_score:.2f}
"""


@dataclass
class PromptPerformance:
    """Track prompt performance for optimization"""
    prompt_template: str
    mode: str
    success_count: int = 0
    failure_count: int = 0
    avg_response_time: float = 0.0
    avg_quality_score: float = 0.0
    last_used: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0


class ConversationMemory:
    """Manages conversation history and context"""
    
    def __init__(self, max_turns: int = 10, persistence_path: Optional[Path] = None):
        """
        Initialize conversation memory
        
        Args:
            max_turns: Maximum turns to keep in memory
            persistence_path: Optional path to persist memory
        """
        self.max_turns = max_turns
        self.persistence_path = persistence_path
        self.turns: deque = deque(maxlen=max_turns)
        self.context: Dict[str, Any] = {}
        self.mode_summaries: Dict[str, str] = {}
        
        if persistence_path and persistence_path.exists():
            self._load_memory()
    
    def add_turn(self, mode: str, prompt: str, response: str, success: bool = True, metadata: Dict[str, Any] = None):
        """Add a conversation turn"""
        turn = ConversationTurn(
            timestamp=datetime.now(),
            mode=mode,
            prompt=prompt,
            response=response,
            success=success,
            metadata=metadata or {}
        )
        self.turns.append(turn)
        
        # Update mode summary
        if success:
            self.mode_summaries[mode] = self._summarize_response(response)
        
        if self.persistence_path:
            self._save_memory()
    
    def get_context_for_mode(self, mode: str) -> str:
        """Get relevant context for a specific mode"""
        context_parts = []
        
        # Add recent turns from same mode
        same_mode_turns = [t for t in self.turns if t.mode == mode][-3:]
        if same_mode_turns:
            context_parts.append("Recent interactions in this mode:")
            for turn in same_mode_turns:
                context_parts.append(f"- {turn.response[:200]}...")
        
        # Add summaries from prerequisite modes
        prereq_modes = self._get_prerequisite_modes(mode)
        for prereq in prereq_modes:
            if prereq in self.mode_summaries:
                context_parts.append(f"\nSummary from {prereq}:")
                context_parts.append(self.mode_summaries[prereq])
        
        # Add persistent context
        if self.context:
            context_parts.append("\nProject context:")
            context_parts.append(json.dumps(self.context, indent=2))
        
        return "\n".join(context_parts)
    
    def update_context(self, key: str, value: Any):
        """Update persistent context"""
        self.context[key] = value
        if self.persistence_path:
            self._save_memory()
    
    def _summarize_response(self, response: str, max_length: int = 500) -> str:
        """Create summary of response for future reference"""
        # Simple truncation for now; could use LLM for better summarization
        if len(response) <= max_length:
            return response
        return response[:max_length] + "..."
    
    def _get_prerequisite_modes(self, mode: str) -> List[str]:
        """Get modes that should inform the current mode"""
        prerequisites = {
            "0": [],
            "0.5": [],
            "1": ["0.5", "0"],
            "2": ["1", "0"],
            "3": ["2", "1"],
            "4": ["3", "2"],
            "5": ["4", "3"],
            "6": ["5", "4"],
            "6.5": ["6", "5"],
            "7": ["6.5", "6"]
        }
        return prerequisites.get(mode, [])
    
    def _save_memory(self):
        """Persist memory to disk"""
        if not self.persistence_path:
            return
        
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "turns": [
                {
                    "timestamp": t.timestamp.isoformat(),
                    "mode": t.mode,
                    "prompt": t.prompt,
                    "response": t.response,
                    "success": t.success,
                    "metadata": t.metadata
                }
                for t in self.turns
            ],
            "context": self.context,
            "mode_summaries": self.mode_summaries
        }
        
        with open(self.persistence_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_memory(self):
        """Load memory from disk"""
        if not self.persistence_path or not self.persistence_path.exists():
            return
        
        with open(self.persistence_path) as f:
            data = json.load(f)
        
        # Restore turns
        for turn_data in data.get("turns", []):
            turn = ConversationTurn(
                timestamp=datetime.fromisoformat(turn_data["timestamp"]),
                mode=turn_data["mode"],
                prompt=turn_data["prompt"],
                response=turn_data["response"],
                success=turn_data["success"],
                metadata=turn_data.get("metadata", {})
            )
            self.turns.append(turn)
        
        self.context = data.get("context", {})
        self.mode_summaries = data.get("mode_summaries", {})


class FewShotLearner:
    """Manages few-shot examples for improved generation"""
    
    def __init__(self, examples_path: Optional[Path] = None):
        """
        Initialize few-shot learner
        
        Args:
            examples_path: Path to store/load examples
        """
        self.examples_path = examples_path
        self.examples_by_mode: Dict[str, List[FewShotExample]] = {}
        self.max_examples_per_mode = 5
        
        if examples_path and examples_path.exists():
            self._load_examples()
    
    def add_example(self, mode: str, input_context: Dict[str, Any], 
                   prompt: str, response: str, quality_score: float,
                   artifact_id: Optional[str] = None):
        """Add a new few-shot example"""
        example = FewShotExample(
            mode=mode,
            input_context=input_context,
            prompt=prompt,
            response=response,
            quality_score=quality_score,
            artifact_id=artifact_id
        )
        
        if mode not in self.examples_by_mode:
            self.examples_by_mode[mode] = []
        
        # Add and maintain top examples
        self.examples_by_mode[mode].append(example)
        self.examples_by_mode[mode].sort(key=lambda x: x.quality_score, reverse=True)
        self.examples_by_mode[mode] = self.examples_by_mode[mode][:self.max_examples_per_mode]
        
        if self.examples_path:
            self._save_examples()
    
    def get_examples_for_mode(self, mode: str, n: int = 3) -> List[FewShotExample]:
        """Get top n examples for a mode"""
        if mode not in self.examples_by_mode:
            return []
        return self.examples_by_mode[mode][:n]
    
    def format_examples_for_prompt(self, mode: str, n: int = 2) -> str:
        """Format examples as text for inclusion in prompt"""
        examples = self.get_examples_for_mode(mode, n)
        if not examples:
            return ""
        
        formatted = ["Here are successful examples from previous runs:\n"]
        for i, example in enumerate(examples, 1):
            formatted.append(f"Example {i}:")
            formatted.append(example.to_prompt_text())
            formatted.append("-" * 40)
        
        return "\n".join(formatted)
    
    def _save_examples(self):
        """Save examples to disk"""
        if not self.examples_path:
            return
        
        self.examples_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {}
        for mode, examples in self.examples_by_mode.items():
            data[mode] = [
                {
                    "input_context": ex.input_context,
                    "prompt": ex.prompt,
                    "response": ex.response,
                    "quality_score": ex.quality_score,
                    "artifact_id": ex.artifact_id
                }
                for ex in examples
            ]
        
        with open(self.examples_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_examples(self):
        """Load examples from disk"""
        if not self.examples_path or not self.examples_path.exists():
            return
        
        with open(self.examples_path) as f:
            data = json.load(f)
        
        for mode, examples_data in data.items():
            self.examples_by_mode[mode] = []
            for ex_data in examples_data:
                example = FewShotExample(
                    mode=mode,
                    input_context=ex_data["input_context"],
                    prompt=ex_data["prompt"],
                    response=ex_data["response"],
                    quality_score=ex_data["quality_score"],
                    artifact_id=ex_data.get("artifact_id")
                )
                self.examples_by_mode[mode].append(example)


class PromptOptimizer:
    """Dynamically optimizes prompts based on performance"""
    
    def __init__(self, optimization_path: Optional[Path] = None):
        """
        Initialize prompt optimizer
        
        Args:
            optimization_path: Path to store optimization data
        """
        self.optimization_path = optimization_path
        self.prompt_templates: Dict[str, List[str]] = self._initialize_templates()
        self.performance_data: Dict[str, PromptPerformance] = {}
        self.exploration_rate = 0.1  # Epsilon for exploration vs exploitation
        
        if optimization_path and optimization_path.exists():
            self._load_optimization_data()
    
    def _initialize_templates(self) -> Dict[str, List[str]]:
        """Initialize prompt template variants"""
        return {
            "0": [
                "Analyze this dataset and provide comprehensive EDA insights:",
                "Perform exploratory data analysis on the following dataset:",
                "Generate a detailed statistical analysis of this data:"
            ],
            "1": [
                "Frame the ML problem with clear hypotheses and success criteria:",
                "Define the decision intelligence framework for this ML task:",
                "Establish hypotheses and KPIs for the following ML objective:"
            ],
            "2": [
                "Assess the feasibility of this ML approach:",
                "Evaluate whether this ML solution is technically viable:",
                "Conduct a feasibility study for the proposed ML system:"
            ],
            "3": [
                "Design the feature engineering and model strategy:",
                "Create a comprehensive ML strategy including features and models:",
                "Develop the technical strategy for feature and model selection:"
            ],
            "4": [
                "Define business metrics and success thresholds:",
                "Establish the business case with measurable outcomes:",
                "Create performance metrics and business value framework:"
            ],
            "5": [
                "Generate production-ready ML code:",
                "Create a complete ML pipeline implementation:",
                "Write optimized production code for the ML system:"
            ]
        }
    
    def get_optimal_prompt(self, mode: str, base_prompt: str, explore: bool = True) -> Tuple[str, str]:
        """
        Get optimal prompt template for mode
        
        Args:
            mode: Current mode
            base_prompt: Base prompt content
            explore: Whether to explore new templates
            
        Returns:
            Tuple of (template, full_prompt)
        """
        import random
        
        templates = self.prompt_templates.get(mode, [base_prompt])
        
        # Epsilon-greedy selection
        if explore and random.random() < self.exploration_rate:
            # Explore: choose random template
            template = random.choice(templates)
        else:
            # Exploit: choose best performing template
            template = self._get_best_template(mode, templates)
        
        # Combine template with base prompt
        full_prompt = f"{template}\n\n{base_prompt}"
        
        return template, full_prompt
    
    def record_performance(self, mode: str, template: str, success: bool, 
                          response_time: float, quality_score: float = 0.5):
        """Record prompt performance for optimization"""
        key = f"{mode}:{hashlib.md5(template.encode()).hexdigest()[:8]}"
        
        if key not in self.performance_data:
            self.performance_data[key] = PromptPerformance(
                prompt_template=template,
                mode=mode
            )
        
        perf = self.performance_data[key]
        
        # Update performance metrics
        if success:
            perf.success_count += 1
        else:
            perf.failure_count += 1
        
        # Update rolling averages
        total = perf.success_count + perf.failure_count
        perf.avg_response_time = (perf.avg_response_time * (total - 1) + response_time) / total
        perf.avg_quality_score = (perf.avg_quality_score * (total - 1) + quality_score) / total
        perf.last_used = datetime.now()
        
        if self.optimization_path:
            self._save_optimization_data()
    
    def _get_best_template(self, mode: str, templates: List[str]) -> str:
        """Get best performing template based on historical data"""
        best_score = -1
        best_template = templates[0]  # Default to first
        
        for template in templates:
            key = f"{mode}:{hashlib.md5(template.encode()).hexdigest()[:8]}"
            if key in self.performance_data:
                perf = self.performance_data[key]
                # Score based on success rate and quality
                score = perf.success_rate * 0.7 + perf.avg_quality_score * 0.3
                if score > best_score:
                    best_score = score
                    best_template = template
        
        return best_template
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate performance report for all prompts"""
        report = {}
        
        for mode in self.prompt_templates.keys():
            mode_data = []
            for key, perf in self.performance_data.items():
                if perf.mode == mode:
                    mode_data.append({
                        "template": perf.prompt_template[:50] + "...",
                        "success_rate": perf.success_rate,
                        "avg_quality": perf.avg_quality_score,
                        "avg_time": perf.avg_response_time,
                        "total_uses": perf.success_count + perf.failure_count
                    })
            
            if mode_data:
                report[mode] = sorted(mode_data, key=lambda x: x["success_rate"], reverse=True)
        
        return report
    
    def _save_optimization_data(self):
        """Save optimization data to disk"""
        if not self.optimization_path:
            return
        
        self.optimization_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {}
        for key, perf in self.performance_data.items():
            data[key] = {
                "prompt_template": perf.prompt_template,
                "mode": perf.mode,
                "success_count": perf.success_count,
                "failure_count": perf.failure_count,
                "avg_response_time": perf.avg_response_time,
                "avg_quality_score": perf.avg_quality_score,
                "last_used": perf.last_used.isoformat() if perf.last_used else None
            }
        
        with open(self.optimization_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_optimization_data(self):
        """Load optimization data from disk"""
        if not self.optimization_path or not self.optimization_path.exists():
            return
        
        with open(self.optimization_path) as f:
            data = json.load(f)
        
        for key, perf_data in data.items():
            self.performance_data[key] = PromptPerformance(
                prompt_template=perf_data["prompt_template"],
                mode=perf_data["mode"],
                success_count=perf_data["success_count"],
                failure_count=perf_data["failure_count"],
                avg_response_time=perf_data["avg_response_time"],
                avg_quality_score=perf_data["avg_quality_score"],
                last_used=datetime.fromisoformat(perf_data["last_used"]) if perf_data["last_used"] else None
            )


class EnhancedLLMProvider:
    """Enhanced LLM provider with intelligence features"""
    
    def __init__(self, 
                 base_provider,
                 project_path: Optional[Path] = None,
                 enable_memory: bool = True,
                 enable_few_shot: bool = True,
                 enable_optimization: bool = True):
        """
        Initialize enhanced LLM provider
        
        Args:
            base_provider: Base LLM provider (Anthropic, Ollama, etc.)
            project_path: Project path for storing intelligence data
            enable_memory: Enable conversation memory
            enable_few_shot: Enable few-shot learning
            enable_optimization: Enable prompt optimization
        """
        self.base_provider = base_provider
        self.project_path = project_path
        
        # Initialize intelligence components
        intelligence_dir = project_path / ".meridian" / "intelligence" if project_path else None
        
        self.memory = None
        if enable_memory:
            memory_path = intelligence_dir / "memory.json" if intelligence_dir else None
            self.memory = ConversationMemory(persistence_path=memory_path)
        
        self.few_shot = None
        if enable_few_shot:
            examples_path = intelligence_dir / "examples.json" if intelligence_dir else None
            self.few_shot = FewShotLearner(examples_path=examples_path)
        
        self.optimizer = None
        if enable_optimization:
            opt_path = intelligence_dir / "optimization.json" if intelligence_dir else None
            self.optimizer = PromptOptimizer(optimization_path=opt_path)
    
    def complete_structured(self,
                           prompt: str,
                           schema: Type[BaseModel],
                           mode: Optional[str] = None,
                           system: Optional[str] = None,
                           **kwargs) -> BaseModel:
        """
        Complete with structured output using intelligence features
        
        Args:
            prompt: Base prompt
            schema: Pydantic schema for structured output
            mode: Current mode for context
            system: System prompt
            
        Returns:
            Validated Pydantic model instance
        """
        # Enhance prompt with intelligence features
        enhanced_prompt = self._enhance_prompt(prompt, mode)
        
        # Call base provider's complete_structured
        return self.base_provider.complete_structured(
            enhanced_prompt,
            schema=schema,
            system=system,
            **kwargs
        )
    
    def complete(self, 
                prompt: str,
                mode: Optional[str] = None,
                schema: Optional[Type[BaseModel]] = None,
                max_tokens: int = 4096,
                temperature: float = 0.3,
                **kwargs) -> str:
        """
        Enhanced completion with intelligence features
        
        Args:
            prompt: Base prompt
            mode: Current mode for context
            schema: Optional Pydantic schema for structured output
            max_tokens: Maximum tokens
            temperature: Temperature for generation
            
        Returns:
            Generated response
        """
        import time
        start_time = time.time()
        
        # Enhance prompt with intelligence features
        enhanced_prompt = self._enhance_prompt(prompt, mode)
        
        # Get optimal prompt template if optimizer enabled
        if self.optimizer and mode:
            template, enhanced_prompt = self.optimizer.get_optimal_prompt(mode, enhanced_prompt)
        else:
            template = None
        
        try:
            # Call base provider
            if schema:
                response = self.base_provider.complete_structured(
                    enhanced_prompt, 
                    schema=schema,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            else:
                response = self.base_provider.complete(
                    enhanced_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
            
            response_time = time.time() - start_time
            
            # Record success
            if self.memory and mode:
                self.memory.add_turn(mode, prompt, response, success=True)
            
            if self.optimizer and template:
                self.optimizer.record_performance(
                    mode, template, success=True, 
                    response_time=response_time, quality_score=0.8
                )
            
            # Consider adding as few-shot example if high quality
            if self.few_shot and mode and response_time < 5.0:  # Fast response = likely good
                self._consider_as_example(mode, prompt, response)
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Record failure
            if self.memory and mode:
                self.memory.add_turn(mode, prompt, str(e), success=False)
            
            if self.optimizer and template:
                self.optimizer.record_performance(
                    mode, template, success=False,
                    response_time=response_time, quality_score=0.0
                )
            
            raise
    
    def _enhance_prompt(self, prompt: str, mode: Optional[str] = None) -> str:
        """Enhance prompt with memory and examples"""
        enhanced_parts = []
        
        # Add conversation context
        if self.memory and mode:
            context = self.memory.get_context_for_mode(mode)
            if context:
                enhanced_parts.append("=== CONTEXT FROM PREVIOUS INTERACTIONS ===")
                enhanced_parts.append(context)
                enhanced_parts.append("")
        
        # Add few-shot examples
        if self.few_shot and mode:
            examples = self.few_shot.format_examples_for_prompt(mode)
            if examples:
                enhanced_parts.append("=== SUCCESSFUL EXAMPLES ===")
                enhanced_parts.append(examples)
                enhanced_parts.append("")
        
        # Add domain knowledge
        domain_knowledge = self._get_domain_knowledge(mode)
        if domain_knowledge:
            enhanced_parts.append("=== DOMAIN KNOWLEDGE ===")
            enhanced_parts.append(domain_knowledge)
            enhanced_parts.append("")
        
        # Add original prompt
        enhanced_parts.append("=== CURRENT REQUEST ===")
        enhanced_parts.append(prompt)
        
        return "\n".join(enhanced_parts)
    
    def _get_domain_knowledge(self, mode: Optional[str]) -> str:
        """Get domain-specific knowledge for mode"""
        if not mode:
            return ""
        
        knowledge = {
            "0": """
Key EDA considerations:
- Check for missing values, outliers, and data quality issues
- Analyze distributions for numerical features
- Examine cardinality for categorical features
- Identify correlations and relationships
- Consider data transformations needed
""",
            "1": """
Decision Intelligence best practices:
- Frame clear, testable hypotheses
- Define measurable KPIs aligned with business goals
- Consider both technical and business constraints
- Identify risks and mitigation strategies
""",
            "2": """
Feasibility assessment criteria:
- Data sufficiency and quality
- Signal strength validation
- Technical complexity vs available resources
- Timeline and budget constraints
- Risk assessment
""",
            "3": """
Feature engineering strategies:
- Domain-specific feature creation
- Interaction and polynomial features
- Encoding strategies for categorical variables
- Scaling and normalization approaches
- Feature selection methods
""",
            "4": """
Business case elements:
- ROI calculation and value proposition
- Success metrics and KPIs
- Risk-adjusted returns
- Implementation costs
- Monitoring and maintenance plans
""",
            "5": """
Code generation best practices:
- Modular, maintainable architecture
- Comprehensive error handling
- Logging and monitoring
- Performance optimization
- Documentation and testing
"""
        }
        
        return knowledge.get(mode, "")
    
    def _consider_as_example(self, mode: str, prompt: str, response: str):
        """Consider adding response as few-shot example"""
        # Simple heuristic: add if response is substantial
        if len(response) > 100:
            # Calculate simple quality score based on length and structure
            quality_score = min(1.0, len(response) / 1000)
            if "{" in response and "}" in response:  # Likely structured
                quality_score += 0.2
            
            quality_score = min(1.0, quality_score)
            
            if quality_score > 0.5:
                self.few_shot.add_example(
                    mode=mode,
                    input_context={"prompt_length": len(prompt)},
                    prompt=prompt[:500],  # Truncate for storage
                    response=response[:1000],  # Truncate for storage
                    quality_score=quality_score
                )
    
    def update_context(self, key: str, value: Any):
        """Update persistent context"""
        if self.memory:
            self.memory.update_context(key, value)
    
    def add_healing_example(self, error_type: str, fix: str, success: bool):
        """
        Store successful healing attempts as few-shot examples.
        
        Args:
            error_type: Type of error that was healed
            fix: The fix that was applied
            success: Whether the healing was successful
        """
        if success and self.few_shot:
            # Create a healing example
            self.few_shot.add_example(
                mode="healer",
                input_context={"error_type": error_type},
                prompt=f"Fix {error_type} error",
                response=str(fix),
                quality_score=1.0
            )
            
            # Also add to memory if available
            if self.memory:
                self.memory.add_turn(
                    mode="healer",
                    prompt=f"Heal {error_type}",
                    response=f"Applied fix: {fix}",
                    success=True,
                    metadata={"error_type": error_type, "fix": fix}
                )
    
    def get_healing_history(self) -> List[Dict[str, Any]]:
        """
        Get history of healing attempts.
        
        Returns:
            List of healing examples
        """
        if self.few_shot and "healer" in self.few_shot.examples_by_mode:
            return [
                {
                    "error_type": ex.input_context.get("error_type"),
                    "fix": ex.response,
                    "quality": ex.quality_score
                }
                for ex in self.few_shot.examples_by_mode["healer"]
            ]
        return []
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get intelligence performance report"""
        report = {
            "memory_turns": len(self.memory.turns) if self.memory else 0,
            "few_shot_examples": sum(len(ex) for ex in self.few_shot.examples_by_mode.values()) if self.few_shot else 0,
        }
        
        if self.optimizer:
            report["prompt_optimization"] = self.optimizer.get_performance_report()
        
        # Add healing stats
        if self.few_shot and "healer" in self.few_shot.examples_by_mode:
            report["healing_examples"] = len(self.few_shot.examples_by_mode["healer"])
        
        return report


def create_enhanced_provider(config: Dict[str, Any], project_path: Optional[Path] = None):
    """
    Factory function to create enhanced LLM provider
    
    Args:
        config: LLM configuration
        project_path: Project path for intelligence data
        
    Returns:
        Enhanced LLM provider instance
    """
    from meridian.llm.providers import get_provider
    
    # Get base provider
    base_provider = get_provider(config)
    
    # Check if intelligence features are enabled
    intelligence_config = config.get("intelligence", {})
    if not intelligence_config.get("enabled", True):
        return base_provider
    
    # Create enhanced provider
    return EnhancedLLMProvider(
        base_provider=base_provider,
        project_path=project_path,
        enable_memory=intelligence_config.get("memory", True),
        enable_few_shot=intelligence_config.get("few_shot", True),
        enable_optimization=intelligence_config.get("optimization", True)
    )