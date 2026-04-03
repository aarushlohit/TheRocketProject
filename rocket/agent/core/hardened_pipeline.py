"""
HARDENED MODEL CALLING MODULE — Production-Ready Fault-Tolerant Pipeline

Features:
- Circuit breaker pattern
- Exponential backoff retry
- Rate limiting
- Image validation
- Comprehensive logging
- Graceful degradation
"""

from __future__ import annotations

import json
import time
import urllib.parse
from typing import Optional, Tuple

import requests

from agent.core.circuit_breaker import get_circuit_breaker, CircuitBreaker
from agent.core.rate_limiter import get_rate_limiter


# =============================================================================
# CONFIGURATION
# =============================================================================

# Request settings
REQUEST_TIMEOUT = 30  # seconds (reduced from 90)
MAX_RETRIES = 3  # Per model

# Confidence threshold
CONFIDENCE_THRESHOLD = 0.7

# Endpoints
GEMINI_ENDPOINT = "https://gen.pollinations.ai/v1/chat/completions"
QWEN_ENDPOINT_TEMPLATE = "https://gen.pollinations.ai/text/{prompt}?model=qwen-vision&image={image}"

# System prompt
SYSTEM_PROMPT = """
You are an assistive AI system that interprets handwritten commands.

CRITICAL:
Return ONLY valid JSON. No explanation. No markdown.

TASK:
- Extract text from image
- Correct spelling
- Infer intent

SUPPORTED INTENTS:
OPEN_APP → {"app": "<name>"}
OPEN_URL → {"url": "<url>"}
SEARCH_WEB → {"query": "<text>"}
TYPE_TEXT → {"text": "<text>"}
PRESS_KEYS → {"keys": "<combo>"}
UNKNOWN → {}

RULES:
- Fix spelling errors
- Do NOT invent apps
- If unclear → UNKNOWN
- Confidence between 0 and 1

OUTPUT FORMAT:
{
  "intent": "",
  "slots": {},
  "confidence": 0.0,
  "normalized_text": ""
}
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def clean_json_response(text: str) -> str:
    """Clean JSON response by removing markdown code blocks."""
    text = text.strip()
    
    # Handle ```json ... ``` blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    return text.strip()


def parse_json_safe(text: str) -> dict:
    """
    Safely parse JSON with fallback.
    
    Returns parsed dict or UNKNOWN intent on failure.
    """
    try:
        clean_text = clean_json_response(text)
        parsed = json.loads(clean_text)
        
        # Ensure required fields
        if "intent" not in parsed:
            parsed["intent"] = "UNKNOWN"
        if "slots" not in parsed:
            parsed["slots"] = {}
        if "confidence" not in parsed:
            parsed["confidence"] = 0.0
        if "normalized_text" not in parsed:
            parsed["normalized_text"] = ""
        
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"[JSON PARSE ERROR] {e}")
        print(f"[RAW CONTENT] {text[:200]}...")
        
        return {
            "intent": "UNKNOWN",
            "slots": {},
            "confidence": 0.0,
            "normalized_text": "",
            "_parse_error": str(e),
        }


def classify_http_error(status_code: int) -> Tuple[str, bool]:
    """
    Classify HTTP error code.
    
    Returns: (error_description, is_retryable)
    """
    if status_code == 522:
        return "Connection timeout (Cloudflare 522) - backend overloaded", True
    elif status_code == 521:
        return "Origin server down (Cloudflare 521)", True
    elif status_code == 520:
        return "Unknown Cloudflare error (520)", True
    elif status_code == 524:
        return "Origin timeout (Cloudflare 524)", True
    elif status_code == 429:
        return "Rate limit exceeded", True
    elif status_code == 401:
        return "Invalid API key", False
    elif status_code == 403:
        return "Forbidden", False
    elif status_code == 404:
        return "Endpoint not found", False
    elif status_code == 500:
        return "Server error", True
    elif status_code == 502:
        return "Bad gateway", True
    elif status_code == 503:
        return "Service unavailable", True
    else:
        return f"HTTP {status_code}", status_code >= 500


# =============================================================================
# IMAGE VALIDATION
# =============================================================================

def validate_image_url(image_url: str, timeout: int = 10) -> Tuple[bool, str, dict]:
    """
    Validate that image URL is accessible.
    
    Returns: (is_valid, message, info)
    """
    print(f"\n========== [IMAGE VALIDATION] ==========")
    print(f"[IMAGE URL] {image_url[:100]}...")
    
    try:
        response = requests.head(image_url, timeout=timeout, allow_redirects=True)
        
        info = {
            "status_code": response.status_code,
            "content_type": response.headers.get("Content-Type", "unknown"),
            "content_length": response.headers.get("Content-Length", "unknown"),
        }
        
        print(f"[STATUS] {response.status_code}")
        print(f"[CONTENT-TYPE] {info['content_type']}")
        print(f"[SIZE] {info['content_length']} bytes")
        
        if response.status_code == 200:
            print(f"[IMAGE VALID] ✓")
            return True, "valid", info
        else:
            print(f"[IMAGE INVALID] HTTP {response.status_code}")
            return False, f"http_{response.status_code}", info
            
    except requests.exceptions.Timeout:
        print(f"[IMAGE ERROR] Timeout")
        return False, "timeout", {}
    except requests.exceptions.ConnectionError as e:
        print(f"[IMAGE ERROR] Connection error: {e}")
        return False, "connection_error", {}
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
        return False, str(e), {}


# =============================================================================
# MODEL CALLERS WITH RETRY
# =============================================================================

def call_gemini_with_retry(
    image_url: str,
    api_key: str,
    circuit_breaker: CircuitBreaker,
    max_retries: int = MAX_RETRIES,
) -> Tuple[Optional[dict], str]:
    """
    Call Gemini with retry logic and circuit breaker.
    
    Returns: (result, error_message)
    """
    # Check circuit breaker
    if not circuit_breaker.is_available("gemini"):
        return None, "circuit_breaker_open"
    
    print(f"\n========== [GEMINI REQUEST] ==========")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": "gemini-fast",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SYSTEM_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
    }
    
    print(f"[MODEL] gemini-fast")
    print(f"[IMAGE URL] {image_url[:80]}...")
    print(f"[TIMEOUT] {REQUEST_TIMEOUT}s")
    
    last_error = ""
    
    for attempt in range(max_retries):
        # Exponential backoff delay (except first attempt)
        if attempt > 0:
            delay = 2 ** attempt  # 2s, 4s, 8s
            print(f"[RETRY] Waiting {delay}s before attempt {attempt + 1}...")
            time.sleep(delay)
        
        print(f"\n[ATTEMPT {attempt + 1}/{max_retries}]")
        
        try:
            # Rate limit
            get_rate_limiter().sync_acquire()
            
            response = requests.post(
                GEMINI_ENDPOINT,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            
            print(f"[STATUS] {response.status_code}")
            
            # Handle non-200
            if response.status_code != 200:
                error_desc, is_retryable = classify_http_error(response.status_code)
                print(f"[ERROR] {error_desc}")
                print(f"[BODY] {response.text[:300]}")
                
                last_error = error_desc
                
                if not is_retryable:
                    circuit_breaker.record_failure("gemini", last_error)
                    return None, last_error
                
                continue  # Retry
            
            # Parse response
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            print(f"\n========== [GEMINI RAW OUTPUT] ==========")
            print(content[:500])
            
            # Parse JSON
            parsed = parse_json_safe(content)
            
            print(f"\n========== [PARSED JSON] ==========")
            print(json.dumps(parsed, indent=2))
            
            # Record success
            circuit_breaker.record_success("gemini")
            print(f"[GEMINI SUCCESS] ✓")
            
            return parsed, ""
            
        except requests.exceptions.Timeout:
            print(f"[TIMEOUT] Request exceeded {REQUEST_TIMEOUT}s")
            last_error = "timeout"
            
        except requests.exceptions.ConnectionError as e:
            print(f"[CONNECTION ERROR] {e}")
            last_error = f"connection_error: {e}"
            
        except json.JSONDecodeError as e:
            print(f"[RESPONSE PARSE ERROR] {e}")
            last_error = f"response_parse_error: {e}"
            
        except Exception as e:
            print(f"[ERROR] {e}")
            last_error = str(e)
    
    # All retries exhausted
    print(f"[GEMINI FAILED] All {max_retries} attempts failed")
    circuit_breaker.record_failure("gemini", last_error)
    return None, last_error


def call_qwen_with_retry(
    image_url: str,
    api_key: str,
    circuit_breaker: CircuitBreaker,
    max_retries: int = MAX_RETRIES,
) -> Tuple[Optional[dict], str]:
    """
    Call Qwen with retry logic and circuit breaker.
    
    Returns: (result, error_message)
    """
    # Check circuit breaker
    if not circuit_breaker.is_available("qwen"):
        return None, "circuit_breaker_open"
    
    print(f"\n========== [QWEN FALLBACK REQUEST] ==========")
    
    # Build URL
    prompt_encoded = urllib.parse.quote(SYSTEM_PROMPT)
    image_encoded = urllib.parse.quote(image_url)
    url = f"https://gen.pollinations.ai/text/{prompt_encoded}?model=qwen-vision&image={image_encoded}"
    
    # Check URL length (GET requests have limits)
    if len(url) > 2000:
        print(f"[WARNING] URL very long ({len(url)} chars) - may fail")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    print(f"[MODEL] qwen-vision")
    print(f"[URL LENGTH] {len(url)} chars")
    
    last_error = ""
    
    for attempt in range(max_retries):
        # Exponential backoff delay (except first attempt)
        if attempt > 0:
            delay = 2 ** attempt  # 2s, 4s, 8s
            print(f"[RETRY] Waiting {delay}s before attempt {attempt + 1}...")
            time.sleep(delay)
        
        print(f"\n[ATTEMPT {attempt + 1}/{max_retries}]")
        
        try:
            # Rate limit
            get_rate_limiter().sync_acquire()
            
            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            
            print(f"[STATUS] {response.status_code}")
            
            # Handle non-200
            if response.status_code != 200:
                error_desc, is_retryable = classify_http_error(response.status_code)
                print(f"[ERROR] {error_desc}")
                print(f"[BODY] {response.text[:300]}")
                
                last_error = error_desc
                
                if not is_retryable:
                    circuit_breaker.record_failure("qwen", last_error)
                    return None, last_error
                
                continue  # Retry
            
            # Get content
            content = response.text
            
            print(f"\n========== [QWEN RAW OUTPUT] ==========")
            print(content[:500])
            
            # Parse JSON
            parsed = parse_json_safe(content)
            
            print(f"\n========== [PARSED JSON] ==========")
            print(json.dumps(parsed, indent=2))
            
            # Record success
            circuit_breaker.record_success("qwen")
            print(f"[QWEN SUCCESS] ✓")
            
            return parsed, ""
            
        except requests.exceptions.Timeout:
            print(f"[TIMEOUT] Request exceeded {REQUEST_TIMEOUT}s")
            last_error = "timeout"
            
        except requests.exceptions.ConnectionError as e:
            print(f"[CONNECTION ERROR] {e}")
            last_error = f"connection_error: {e}"
            
        except Exception as e:
            print(f"[ERROR] {e}")
            last_error = str(e)
    
    # All retries exhausted
    print(f"[QWEN FAILED] All {max_retries} attempts failed")
    circuit_breaker.record_failure("qwen", last_error)
    return None, last_error


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def call_model_hardened(
    image_url: str,
    api_key: str,
    validate_image: bool = True,
) -> dict:
    """
    HARDENED model call with full fault tolerance.
    
    Pipeline:
    1. Validate image URL (optional)
    2. Try Gemini with retry
    3. Fallback to Qwen with retry
    4. Return structured result (never crash)
    
    Returns dict with:
    - On success: parsed intent JSON + _model_used
    - On failure: status="error" + reason + retryable flag
    """
    print(f"\n{'='*60}")
    print(f"========== [HARDENED MODEL CALL] ==========")
    print(f"{'='*60}")
    
    circuit_breaker = get_circuit_breaker()
    gemini_error = ""
    qwen_error = ""
    
    # Step 1: Validate image URL
    if validate_image:
        is_valid, message, info = validate_image_url(image_url)
        if not is_valid:
            print(f"[IMAGE INVALID] {message}")
            return {
                "status": "error",
                "reason": "invalid_image",
                "message": f"Image validation failed: {message}",
                "retryable": False,
                "_model_used": "none",
                "_image_info": info,
            }
    
    # Step 2: Try Gemini
    result, gemini_error = call_gemini_with_retry(
        image_url, api_key, circuit_breaker
    )
    
    if result is not None:
        # Check for UNKNOWN intent (trigger fallback)
        if result.get("intent") == "UNKNOWN" and result.get("confidence", 0) < 0.5:
            print(f"[GEMINI] Returned low-confidence UNKNOWN → trying fallback")
        else:
            result["_model_used"] = "gemini-fast"
            return _finalize_result(result)
    
    # Step 3: Fallback to Qwen
    print(f"\n[FALLBACK] Gemini failed, trying Qwen...")
    
    result, qwen_error = call_qwen_with_retry(
        image_url, api_key, circuit_breaker
    )
    
    if result is not None:
        result["_model_used"] = "qwen-vision"
        return _finalize_result(result)
    
    # Step 4: Both models failed
    print(f"\n========== [BOTH MODELS FAILED] ==========")
    print(f"[GEMINI ERROR] {gemini_error}")
    print(f"[QWEN ERROR] {qwen_error}")
    
    return {
        "status": "error",
        "reason": "model_unavailable",
        "message": "Both models failed",
        "retryable": True,
        "_model_used": "none",
        "_gemini_error": gemini_error,
        "_qwen_error": qwen_error,
        "_circuit_breaker": circuit_breaker.get_status(),
    }


def _finalize_result(result: dict) -> dict:
    """Finalize and validate result."""
    
    print(f"\n========== [FINAL PIPELINE TRACE] ==========")
    print(f"[MODEL USED] {result.get('_model_used', 'unknown')}")
    print(f"[INTENT] {result.get('intent', 'N/A')}")
    print(f"[CONFIDENCE] {result.get('confidence', 0)}")
    
    # Add status
    result["status"] = "success"
    
    # Validate confidence
    confidence = result.get("confidence", 0)
    if confidence < CONFIDENCE_THRESHOLD:
        print(f"[CONFIDENCE LOW] {confidence} < {CONFIDENCE_THRESHOLD}")
        result["_confidence_warning"] = f"Below threshold ({CONFIDENCE_THRESHOLD})"
    
    print(f"[EXECUTION READY] ✓")
    
    return result


# =============================================================================
# VALIDATION AND EXECUTION WRAPPER
# =============================================================================

def validate_and_execute_check(parsed_json: dict) -> Tuple[bool, str, dict]:
    """
    Pre-execution validation check.
    
    Returns: (can_execute, reason, details)
    """
    # Check for error status
    if parsed_json.get("status") == "error":
        return False, "model_error", {
            "reason": parsed_json.get("reason"),
            "message": parsed_json.get("message"),
            "retryable": parsed_json.get("retryable", False),
        }
    
    # Check for model failure
    if parsed_json.get("_model_used") == "none":
        return False, "no_model", {
            "message": "No model was able to process the request",
            "retryable": True,
        }
    
    # Check confidence
    confidence = parsed_json.get("confidence", 0)
    if confidence < CONFIDENCE_THRESHOLD:
        return False, "low_confidence", {
            "confidence": confidence,
            "threshold": CONFIDENCE_THRESHOLD,
        }
    
    # Check for UNKNOWN intent
    if parsed_json.get("intent") == "UNKNOWN":
        return False, "unknown_intent", {
            "message": "Could not determine user intent",
        }
    
    return True, "ok", {}


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "call_model_hardened",
    "validate_and_execute_check",
    "validate_image_url",
    "CONFIDENCE_THRESHOLD",
    "SYSTEM_PROMPT",
]
