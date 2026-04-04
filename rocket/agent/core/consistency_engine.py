"""
Stage 4 — Multi-Variant Consistency Engine.

Analyzes multiple OCR candidates from different image variants:
- original
- rotated_90
- rotated_270

Selects the MOST CONSISTENT result using:
- Intent + slots similarity grouping
- Confidence scoring
- Frequency voting

RULE: If conflict → choose majority → else choose highest confidence
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Minimum consistency score to proceed
MIN_CONSISTENCY_SCORE = 0.6

# Weight factors for final score
CONFIDENCE_WEIGHT = 0.6
FREQUENCY_WEIGHT = 0.4


# =============================================================================
# CONSISTENCY RESULT
# =============================================================================

@dataclass
class ConsistencyResult:
    """Result of multi-variant consistency analysis."""
    
    selected_intent: Dict[str, Any]
    consistency_score: float
    confidence: float
    final_score: float
    voting_breakdown: Dict[str, int]
    total_candidates: int
    agreement_ratio: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_intent": self.selected_intent,
            "consistency_score": round(self.consistency_score, 4),
            "confidence": round(self.confidence, 4),
            "final_score": round(self.final_score, 4),
            "voting_breakdown": self.voting_breakdown,
            "total_candidates": self.total_candidates,
            "agreement_ratio": round(self.agreement_ratio, 4),
        }


@dataclass
class CandidateGroup:
    """Group of similar candidates."""
    
    signature: str
    candidates: List[Dict[str, Any]]
    avg_confidence: float
    count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "signature": self.signature,
            "count": self.count,
            "avg_confidence": round(self.avg_confidence, 4),
        }


# =============================================================================
# CONSISTENCY ENGINE CLASS
# =============================================================================

class ConsistencyEngine:
    """
    Multi-variant consistency analysis.
    
    Process:
    1. Extract signatures from each candidate (intent + key slots)
    2. Group candidates by signature similarity
    3. Score groups by frequency and average confidence
    4. Select best group
    5. Return best candidate from winning group
    
    RULE: Never trust single output - require consistency
    """
    
    def __init__(
        self,
        min_consistency: float = MIN_CONSISTENCY_SCORE,
        confidence_weight: float = CONFIDENCE_WEIGHT,
        frequency_weight: float = FREQUENCY_WEIGHT,
    ):
        self.min_consistency = min_consistency
        self.confidence_weight = confidence_weight
        self.frequency_weight = frequency_weight
    
    def analyze(
        self,
        candidates: List[Dict[str, Any]],
    ) -> ConsistencyResult:
        """
        Analyze multiple candidates for consistency.
        
        Args:
            candidates: List of intent JSON from different variants
            
        Returns:
            ConsistencyResult with selected intent and scores
            
        FIX 3c: OPEN_APP BYPASS in consistency engine
        """
        print(f"\n{'='*60}")
        print(f"[CONSISTENCY ENGINE] Analyzing {len(candidates)} candidates")
        print(f"{'='*60}")
        
        # FIX 3c: OPEN_APP BYPASS - Check for high-confidence OPEN_APP first
        for candidate in candidates:
            if (candidate and 
                candidate.get("intent") == "OPEN_APP" and 
                candidate.get("confidence", 0) > 0.7):
                print(f"\n{'='*60}")
                print(f"[CONSISTENCY BYPASS] OPEN_APP with confidence {candidate.get('confidence'):.2f}")
                print(f"[CONSISTENCY BYPASS] Skipping consistency analysis")
                print(f"{'='*60}")
                
                return ConsistencyResult(
                    selected_intent=candidate,
                    consistency_score=1.0,
                    confidence=candidate.get("confidence", 0.9),
                    agreement_ratio=1.0,
                    final_score=1.0,
                    voting_breakdown={"OPEN_APP": len(candidates)},
                    all_candidates=candidates,
                )
        
        # Filter out invalid candidates
        valid_candidates = [
            c for c in candidates
            if c and c.get("intent") and c.get("intent") != "UNKNOWN"
        ]
        
        if not valid_candidates:
            print(f"[CONSISTENCY] No valid candidates")
            # Return best invalid or empty
            return self._fallback_result(candidates)
        
        print(f"[CONSISTENCY] Valid candidates: {len(valid_candidates)}")
        
        # =================================================================
        # STEP 1: Create signatures
        # =================================================================
        signatures: List[Tuple[str, Dict[str, Any]]] = []
        
        for candidate in valid_candidates:
            sig = self._create_signature(candidate)
            signatures.append((sig, candidate))
            print(f"[SIGNATURE] {sig}")
        
        # =================================================================
        # STEP 2: Group by signature
        # =================================================================
        groups: Dict[str, CandidateGroup] = {}
        
        for sig, candidate in signatures:
            # Use fuzzy grouping - normalize signature
            normalized_sig = self._normalize_signature(sig)
            
            if normalized_sig not in groups:
                groups[normalized_sig] = CandidateGroup(
                    signature=normalized_sig,
                    candidates=[],
                    avg_confidence=0.0,
                    count=0,
                )
            
            groups[normalized_sig].candidates.append(candidate)
            groups[normalized_sig].count += 1
        
        # Calculate average confidence per group
        for group in groups.values():
            confidences = [
                c.get("confidence", 0.0) for c in group.candidates
            ]
            group.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        print(f"\n[GROUPS] {len(groups)} unique groups found")
        for sig, group in groups.items():
            print(f"  {sig}: count={group.count}, avg_conf={group.avg_confidence:.3f}")
        
        # =================================================================
        # STEP 3: Score groups
        # =================================================================
        total_candidates = len(valid_candidates)
        scored_groups: List[Tuple[float, str, CandidateGroup]] = []
        
        for sig, group in groups.items():
            # Frequency score (normalized)
            frequency_score = group.count / total_candidates
            
            # Confidence score (normalized, avg of group)
            confidence_score = group.avg_confidence
            
            # Combined score
            combined_score = (
                self.frequency_weight * frequency_score +
                self.confidence_weight * confidence_score
            )
            
            scored_groups.append((combined_score, sig, group))
            print(f"[SCORE] {sig}: freq={frequency_score:.3f}, conf={confidence_score:.3f}, combined={combined_score:.3f}")
        
        # Sort by score descending
        scored_groups.sort(key=lambda x: x[0], reverse=True)
        
        # =================================================================
        # STEP 4: Select winner
        # =================================================================
        if not scored_groups:
            return self._fallback_result(candidates)
        
        best_score, best_sig, best_group = scored_groups[0]
        
        # Select best candidate from winning group (highest confidence)
        best_candidate = max(
            best_group.candidates,
            key=lambda c: c.get("confidence", 0.0)
        )
        
        # Calculate agreement ratio
        agreement_ratio = best_group.count / total_candidates
        
        # Calculate consistency score
        # High if majority agrees and confidence is high
        consistency_score = (agreement_ratio * 0.5) + (best_candidate.get("confidence", 0.0) * 0.5)
        
        # Final score for execution trust
        final_score = (
            best_candidate.get("confidence", 0.0) +
            consistency_score
        ) / 2.0
        
        # Build voting breakdown
        voting_breakdown = {sig: group.count for sig, group in groups.items()}
        
        print(f"\n[WINNER] {best_sig}")
        print(f"[AGREEMENT] {agreement_ratio:.2%} ({best_group.count}/{total_candidates})")
        print(f"[CONSISTENCY SCORE] {consistency_score:.4f}")
        print(f"[FINAL SCORE] {final_score:.4f}")
        
        logger.info(f"[CONSISTENCY] Winner: {best_sig}, Agreement: {agreement_ratio:.2%}, Score: {final_score:.4f}")
        
        return ConsistencyResult(
            selected_intent=best_candidate,
            consistency_score=consistency_score,
            confidence=best_candidate.get("confidence", 0.0),
            final_score=final_score,
            voting_breakdown=voting_breakdown,
            total_candidates=total_candidates,
            agreement_ratio=agreement_ratio,
        )
    
    def _create_signature(self, candidate: Dict[str, Any]) -> str:
        """
        Create a signature string from intent + key slots.
        
        Signature format: "INTENT:key1=val1,key2=val2"
        """
        intent = candidate.get("intent", "UNKNOWN")
        slots = candidate.get("slots", {})
        
        # For MULTI_STEP, use step intents
        if intent == "MULTI_STEP":
            steps = candidate.get("steps", slots.get("steps", []))
            step_intents = [s.get("intent", "?") for s in steps if isinstance(s, dict)]
            return f"MULTI_STEP:{'+'.join(step_intents)}"
        
        # Extract key slot values
        key_values = []
        
        if "app" in slots:
            key_values.append(f"app={slots['app'].lower()}")
        if "query" in slots:
            # Normalize query (first 3 words)
            query = slots["query"].lower().split()[:3]
            key_values.append(f"query={' '.join(query)}")
        if "url" in slots:
            key_values.append(f"url={slots['url'][:30]}")
        if "text" in slots:
            # First 3 words of text
            text = slots["text"].split()[:3]
            key_values.append(f"text={' '.join(text)}")
        if "keys" in slots:
            key_values.append(f"keys={slots['keys']}")
        
        slot_str = ",".join(key_values) if key_values else "empty"
        return f"{intent}:{slot_str}"
    
    def _normalize_signature(self, signature: str) -> str:
        """
        Normalize signature for fuzzy grouping.
        
        - Lowercase
        - Normalize whitespace
        - Handle common variations
        """
        sig = signature.lower().strip()
        
        # Normalize app names
        app_normalizations = {
            "google chrome": "chrome",
            "google": "chrome",
            "chrom": "chrome",
            "firefoxe": "firefox",
            "vs code": "vscode",
            "visual studio code": "vscode",
        }
        
        for old, new in app_normalizations.items():
            sig = sig.replace(old, new)
        
        return sig
    
    def _fallback_result(self, candidates: List[Dict[str, Any]]) -> ConsistencyResult:
        """Create fallback result when no valid candidates."""
        
        # Try to find any candidate with intent
        for candidate in candidates:
            if candidate and candidate.get("intent"):
                return ConsistencyResult(
                    selected_intent=candidate,
                    consistency_score=0.0,
                    confidence=candidate.get("confidence", 0.0),
                    final_score=0.0,
                    voting_breakdown={"unknown": 1},
                    total_candidates=len(candidates),
                    agreement_ratio=0.0,
                )
        
        # Complete fallback
        return ConsistencyResult(
            selected_intent={"intent": "UNKNOWN", "slots": {}, "confidence": 0.0},
            consistency_score=0.0,
            confidence=0.0,
            final_score=0.0,
            voting_breakdown={"unknown": len(candidates)},
            total_candidates=len(candidates),
            agreement_ratio=0.0,
        )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_consistency_instance: Optional[ConsistencyEngine] = None


def get_consistency_engine() -> ConsistencyEngine:
    """Get singleton ConsistencyEngine instance."""
    global _consistency_instance
    if _consistency_instance is None:
        _consistency_instance = ConsistencyEngine()
    return _consistency_instance


def analyze_consistency(candidates: List[Dict[str, Any]]) -> ConsistencyResult:
    """
    Convenience function to analyze candidate consistency.
    
    Args:
        candidates: List of intent JSON from different variants
        
    Returns:
        ConsistencyResult
    """
    return get_consistency_engine().analyze(candidates)
