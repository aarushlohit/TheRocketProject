"""Debug-enhanced model calling functions for Stage 1.5.

Apply this patch to agent/stage0/pipeline.py to replace the model calling functions.
"""

import json
import time
import requests


def validate_image_url(image_url: str) -> tuple[bool, str]:
    """
    Validate that image URL is accessible.
    Returns: (is_valid, message)
    """
    print("\n========== [IMAGE VALIDATION] ==========")
    print(f"[IMAGE URL] {image_url}")
    
    try:
        response = requests.head(image_url, timeout=10)
        print(f"[IMAGE STATUS] {response.status_code}")
        
        if response.status_code == 200:
            size = response.headers.get('Content-Length', 'unknown')
            print(f"[IMAGE SIZE] {size} bytes")
            print(f"[IMAGE VALID] ✓")
            return True, "valid"
        else:
            print(f"[IMAGE ERROR] HTTP {response.status_code}")
            return False, f"image_http_{response.status_code}"
            
    except requests.exceptions.Timeout:
        print(f"[IMAGE ERROR] Timeout accessing image")
        return False, "image_timeout"
    except Exception as e:
        print(f"[IMAGE ERROR] {e}")
        return False, f"image_error: {e}"


# Insert this function before call_gemini
# This validates images before making expensive API calls


def call_gemini_with_debug(image_url: str, api_key: str, SYSTEM_PROMPT: str, retry: int = 2) -> dict:
    """Enhanced Gemini call with comprehensive debugging."""
    url = "https://gen.pollinations.ai/v1/chat/completions"
    
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
    
    print("\n========== [GEMINI REQUEST DEBUG] ==========")
    print(f"[URL] {url}")
    print(f"[MODEL] gemini-fast")
    print(f"[IMAGE URL] {image_url}")
    print(f"[PROMPT LENGTH] {len(SYSTEM_PROMPT)} characters")
    print(f"[API KEY] {'***' + api_key[-8:] if len(api_key) > 8 else '***'}")
    
    # Retry loop
    for attempt in range(retry):
        try:
            print(f"\n[GEMINI ATTEMPT {attempt + 1}/{retry}]")
            
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=30  # Reduced from 90 to fail faster
            )
            
            print(f"[HTTP STATUS] {response.status_code}")
            
            # Handle non-200 responses
            if response.status_code != 200:
                print(f"[ERROR BODY] {response.text[:500]}")
                
                # Common HTTP errors
                if response.status_code == 522:
                    error_msg = "Connection timeout (Cloudflare 522) - Backend overloaded or slow"
                    print(f"\n[522 ERROR ANALYSIS]")
                    print(f"  - Cloudflare connection timeout")
                    print(f"  - Pollinations backend may be slow/down")
                    print(f"  - Image processing taking too long")
                    print(f"  - Possible causes: large image, server load, network issues")
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded"
                elif response.status_code == 401:
                    error_msg = "Invalid API key"
                elif response.status_code == 500:
                    error_msg = "Server error"
                else:
                    error_msg = f"HTTP {response.status_code}"
                
                print(f"[ERROR TYPE] {error_msg}")
                raise Exception(f"Gemini failed: {error_msg}")
            
            # Parse response
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            print("\n========== [GEMINI RAW OUTPUT] ==========")
            print(content[:500])
            
            # Clean and parse JSON (use your clean_json_response function)
            clean_content = content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            elif clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()
            
            try:
                parsed = json.loads(clean_content)
                print("\n========== [PARSED JSON] ==========")
                print(json.dumps(parsed, indent=2))
                
                # Validate required fields
                if "intent" not in parsed:
                    raise Exception("Missing 'intent' field in response")
                
                print(f"[GEMINI SUCCESS] ✓")
                return parsed
                
            except json.JSONDecodeError as je:
                print(f"\n[JSON PARSE ERROR] {je}")
                print(f"[FAILED CONTENT] {clean_content[:200]}")
                raise Exception(f"Invalid JSON from Gemini: {je}")
        
        except requests.exceptions.Timeout:
            print(f"[TIMEOUT] Request took >30 seconds")
            if attempt < retry - 1:
                print(f"[RETRY] Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                raise Exception("Gemini timeout after retries")
        
        except requests.exceptions.ConnectionError as ce:
            print(f"[CONNECTION ERROR] {ce}")
            if attempt < retry - 1:
                print(f"[RETRY] Waiting 2 seconds before retry...")
                time.sleep(2)
            else:
                raise Exception(f"Gemini connection error: {ce}")
        
        except Exception as e:
            if attempt < retry - 1:
                print(f"[RETRY] Attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
            else:
                print(f"[GEMINI FINAL FAILURE] All {retry} attempts failed")
                raise
    
    raise Exception("Gemini: All retry attempts exhausted")


# USAGE:
# Replace your call_gemini function with call_gemini_with_debug
# Also add validate_image_url() before model calls in call_model_with_fallback
