"""
Stage 4 — Execution Trust System.

Computes final execution trust score and determines if execution should proceed:
- Combines confidence + consistency scores
- Applies execution threshold
- Provides execution decision with reasoning

RULE: If final_score < threshold → DO NOT execute → request retry
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum score to allow execution
EXECUTION_THRESHOLD = 0.75

# Individual component thresholds
MIN_CONFIDENCE = 0.6
MIN_CONSISTENCY = 0.5

# Weights for final score calculation
CONFIDENCE_WEIGHT = 0.5
CONSISTENCY_WEIGHT = 0.3
VALIDATION_WEIGHT = 0.2


# =============================================================================
# TRUST DECISION
# =============================================================================

@dataclass
class TrustDecision:
    """Execution trust decision."""
    
    should_execute: bool
    final_score: float
    confidence_score: float
    consistency_score: float
    validation_score: float
    reason: str
    recommendations: list
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "should_execute": self.should_execute,
            "final_score": round(self.final_score, 4),
            "confidence_score": round(self.confidence_score, 4),
            "consistency_score": round(self.consistency_score, 4),
            "validation_score": round(self.validation_score, 4),
            "reason": self.reason,
            "recommendations": self.recommendations,
        }


# =============================================================================
# TRUST EVALUATOR CLASS
# =============================================================================

class TrustEvaluator:
    """
    Evaluates execution trust based on multiple signals.
    
    Signals:
    1. Model confidence (from JSON)
    2. Consistency score (from multi-variant analysis)
    3. Validation score (from JSON validator)
    
    Formula:
    final_score = (confidence * W1) + (consistency * W2) + (validation * W3)
    
    Decision:
    - Execute if final_score >= threshold
    - Reject and request retry if below threshold
    """
    
    def __init__(
        self,
        execution_threshold: float = EXECUTION_THRESHOLD,
        min_confidence: float = MIN_CONFIDENCE,
        min_consistency: float = MIN_CONSISTENCY,
        confidence_weight: float = CONFIDENCE_WEIGHT,
        consistency_weight: float = CONSISTENCY_WEIGHT,
        validation_weight: float = VALIDATION_WEIGHT,
    ):
        self.execution_threshold = execution_threshold
        self.min_confidence = min_confidence
        self.min_consistency = min_consistency
        self.confidence_weight = confidence_weight
        self.consistency_weight = consistency_weight
        self.validation_weight = validation_weight
    
    def evaluate(
        self,
        confidence: float,
        consistency_score: float,
        validation_passed: bool,
        validation_warnings: int = 0,
        intent: Optional[str] = None,
    ) -> TrustDecision:
        """
        Evaluate execution trust.
        
        Args:
            confidence: Model confidence score (0-1)
            consistency_score: Multi-variant consistency (0-1)
            validation_passed: Whether JSON validation passed
            validation_warnings: Number of validation warnings
            
        Returns:
            TrustDecision with execution recommendation
        """
        print(f"\n{'='*60}")
        print(f"[TRUST EVALUATOR] Computing execution trust")
        print(f"{'='*60}")
        
        recommendations = []
        
        # =================================================================
        # COMPUTE INDIVIDUAL SCORES
        # =================================================================
        
        # Confidence score (direct from model)
        confidence_score = min(1.0, max(0.0, confidence))
        print(f"[CONFIDENCE] {confidence_score:.4f}")
        
        # Consistency score (from multi-variant)
        consistency_normalized = min(1.0, max(0.0, consistency_score))
        print(f"[CONSISTENCY] {consistency_normalized:.4f}")
        
        # Validation score
        if validation_passed:
            # Start at 1.0, subtract for warnings
            validation_score = max(0.7, 1.0 - (validation_warnings * 0.1))
        else:
            validation_score = 0.0
        print(f"[VALIDATION] {validation_score:.4f} (passed={validation_passed}, warnings={validation_warnings})")
        
        # =================================================================
        # COMPUTE FINAL SCORE
        # =================================================================
        
        final_score = (
            confidence_score * self.confidence_weight +
            consistency_normalized * self.consistency_weight +
            validation_score * self.validation_weight
        )
        
        print(f"\n[FINAL SCORE] {final_score:.4f}")
        print(f"[THRESHOLD] {self.execution_threshold}")
        
        # =================================================================
        # DETERMINE EXECUTION DECISION
        # =================================================================
        
        # FIX 4: TRUST OVERRIDE for OPEN_APP
        # If OPEN_APP with confidence > 0.7, execute regardless of trust score
        if intent == "OPEN_APP" and confidence_score > 0.7:
            print(f"\n[TRUST OVERRIDE] OPEN_APP with confidence {confidence_score:.2f} > 0.7 - bypassing trust score")
            return TrustDecision(
                should_execute=True,
                final_score=final_score,
                confidence_score=confidence_score,
                consistency_score=consistency_normalized,
                validation_score=validation_score,
                reason=f"OPEN_APP trust override - confidence {confidence_score:.2f} > 0.7",
                recommendations=[],
            )
        
        should_execute = True
        reason = "All checks passed"
        
        # Check validation (hard requirement)
        if not validation_passed:
            should_execute = False
            reason = "Validation failed - invalid intent structure"
            recommendations.append("Fix intent structure before retrying")
        
        # Check minimum confidence
        elif confidence_score < self.min_confidence:
            should_execute = False
            reason = f"Confidence too low ({confidence_score:.2f} < {self.min_confidence})"
            recommendations.append("Request clearer handwriting or retry")
        
        # Check minimum consistency
        elif consistency_normalized < self.min_consistency:
            should_execute = False
            reason = f"Consistency too low ({consistency_normalized:.2f} < {self.min_consistency})"
            recommendations.append("Image variants disagree - retry with clearer image")
        
        # Check final score threshold
        elif final_score < self.execution_threshold:
            should_execute = False
            reason = f"Final score below threshold ({final_score:.2f} < {self.execution_threshold})"
            recommendations.append("Confidence or consistency insufficient")
            recommendations.append("Consider retrying with clearer input")
        
        # All passed
        else:
            reason = f"Trust score {final_score:.2f} exceeds threshold {self.execution_threshold}"
        
        print(f"\n[DECISION] Execute: {should_execute}")
        print(f"[REASON] {reason}")
        if recommendations:
            print(f"[RECOMMENDATIONS] {recommendations}")
        
        logger.info(f"[TRUST] Execute={should_execute}, Score={final_score:.4f}, Reason={reason}")
        
        return TrustDecision(
            should_execute=should_execute,
            final_score=final_score,
            confidence_score=confidence_score,
            consistency_score=consistency_normalized,
            validation_score=validation_score,
            reason=reason,
            recommendations=recommendations,
        )
    
    def quick_check(self, confidence: float) -> bool:
        """
        Quick confidence-only check for single-candidate scenarios.
        
        Returns True if confidence alone is sufficient.
        """
        return confidence >= self.min_confidence


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_trust_instance: Optional[TrustEvaluator] = None


def get_trust_evaluator() -> TrustEvaluator:
    """Get singleton TrustEvaluator instance."""
    global _trust_instance
    if _trust_instance is None:
        _trust_instance = TrustEvaluator()
    return _trust_instance


def evaluate_trust(
    confidence: float,
    consistency_score: float,
    validation_passed: bool,
    validation_warnings: int = 0,
    intent: Optional[str] = None,
) -> TrustDecision:
    """
    Convenience function to evaluate execution trust.
    
    Args:
        confidence: Model confidence score
        consistency_score: Multi-variant consistency
        validation_passed: JSON validation result
        validation_warnings: Number of warnings
        intent: Intent type (for OPEN_APP override)
        
    Returns:
        TrustDecision
    """
    return get_trust_evaluator().evaluate(
        confidence=confidence,
        consistency_score=consistency_score,
        validation_passed=validation_passed,
        validation_warnings=validation_warnings,
        intent=intent,
    )
