# Engineering Principles

These principles guide all decision-making in Rocket development.

---

## 1. Accessibility-First

**Principle**: Rocket is useless if users can't use the toolchain to build it.

**What this means**:
- ✅ All development tools must be accessible (VS Code with a11y plugins)
- ✅ All documentation must be screen-reader friendly
- ✅ Code examples must account for assistive technology
- ✅ Design decisions prioritize accessibility of users AND developers
- ❌ No accessibility-after-the-fact retrofits

**Examples**:
- Build CLI tools instead of assuming GUI usage
- Provide keyboard-only workflows for all features
- Test with actual screen readers (NVDA, JAWS, VoiceOver)
- Document all assumptions about visual/motor ability

---

## 2. Open-Source First

**Principle**: Transparency enables accessibility. Closed systems can hide inaccessibility.

**What this means**:
- ✅ All code under OSI-approved license (MIT preferred)
- ✅ All algorithms open to audit and improvement
- ✅ Dependencies must be open-source (or clearly justified proprietary subset)
- ✅ Community can fork, modify, audit for accessibility
- ❌ Proprietary APIs for core functionality
- ❌ Licensing restrictions on use cases

**Examples**:
- Use Whisper (OpenAI open-source) not Alexa SDK
- Use open OCR libraries, not commercial APIs
- License under MIT, not restrictive GPL

---

## 3. Local-First, Works Offline

**Principle**: Users with limited connectivity or privacy concerns need full functionality without internet.

**What this means**:
- ✅ Core automation works without network
- ✅ Models downloaded once, run locally (or caches locally)
- ✅ No cloud requirement for basic features
- ✅ Optional cloud features degrade gracefully
- ❌ Required internet for core functionality
- ❌ Cloud-only features without offline alternative

**Examples**:
- Voice recognition: Whisper runs locally by default
- Internet-optional: "Go to google.com" falls back to typing URL if offline
- Models stored in user's models/ directory, not streamed

---

## 4. Low Latency

**Principle**: Accessibility users notice every millisecond of lag. Delay = frustration.

**What this means**:
- ✅ Voice input → action < 800ms target
- ✅ Drawing input → feedback < 500ms
- ✅ Optimize database queries, minimize serialization
- ✅ Measure latency in all pull requests
- ❌ Acceptable "processing time" that delays response
- ❌ Synchronous UI blocking

**Performance Budgets**:
- Mobile input capture: 50ms
- Transmission: 100ms
- NLU parsing: 200ms
- Skill execution: varies, but feedback within 200ms
- Total pipeline: < 800ms for deterministic commands

**Examples**:
- Use message queues instead of blocking RPC
- Cache frequently used app paths
- Profile with py-spy, find bottlenecks immediately

---

## 5. Modular Design

**Principle**: Features must be isolated enough that broken skills don't break the system.

**What this means**:
- ✅ Each skill is independent module
- ✅ Skill failures don't crash agent
- ✅ New skills added without modifying core code
- ✅ Easy to test in isolation
- ✅ Clear interfaces between components
- ❌ Monolithic skill implementations
- ❌ Circular dependencies
- ❌ Tight coupling to specific OS APIs

**Modularity Rules**:
- One skill per file/class
- Skill interface is abstract base class
- Skills registered via plug-in system, not hardcoded
- Platform adapters are swappable

**Examples**:
```python
# ✅ Good: Skill is independent module
class LinkedInSkill(BaseSkill):
    def execute(self, intent):
        navigator = self.adapter.get_navigator()
        return navigator.goto("linkedin.com")

# ❌ Bad: Skill depends on other skills, hardcoded paths
class LinkedInSkill(BaseSkill):
    def execute(self, intent):
        BrowserSkill().open_browser()  # Coupled!
        click_absolute(100, 200)  # Hardcoded!
```

---

## 6. Explicit Over Implicit

**Principle**: Avoid magic. When automation is unclear, say so.

**What this means**:
- ✅ Explicit intent parsing (show what was understood)
- ✅ Explicit state changes (log transitions)
- ✅ Explicit errors (don't hide failures)
- ✅ Explicit confirmation (user knows what will happen)
- ❌ Guessing user intent
- ❌ Silent failures
- ❌ Unlogged state changes

**Examples**:
```
User: "Search for restaurants"
Rocket (unclear): Silent action
Rocket (explicit): "I understand you want to search. Search where? Google, Apple Maps, Yelp?"

User: "Type hello"
Rocket (unclear): Types in whatever is focused
Rocket (explicit): "I'll type in Chrome address bar. Continue?" (if target ambiguous)
```

---

## 7. No Overengineering

**Principle**: Build for current requirements, architecture for future ones.

**What this means**:
- ✅ YAGNI (You Aren't Gonna Need It) - don't build features not needed today
- ✅ Simple solutions preferred over clever ones
- ✅ But design for extensibility (skills, platforms)
- ✅ Profile before optimizing
- ❌ Gold-plating features
- ❌ Premature optimization
- ❌ Complex architectures for simple problems

**Examples**:
```python
# ✅ Good: Rule-based NLU in Phase 0, ML models later
if "open" in transcription and "chrome" in transcription:
    return Intent(action="OPEN_APP", app="chrome")

# ❌ Bad: Building transformer NLP model when rules suffice
model = load_bert_model("bert-base-uncased")
# Overkill for simple command parsing in Phase 0
```

---

## 8. Fail-Fast, Fail Loud

**Principle**: Better to crash obviously than silently produce wrong results.

**What this means**:
- ✅ Assertions for invariants
- ✅ Verbose error messages
- ✅ Immediate feedback on user errors
- ✅ Crash tests that verify errors are caught
- ❌ Try-except without logging
- ❌ Silent data corruption
- ❌ Tolerance of invalid states

**Examples**:
```python
# ✅ Good: Fail fast with clear message
def execute_skill(intent):
    assert intent.action in self.SUPPORTED_INTENTS, \
        f"Unknown intent: {intent.action}. Supported: {self.SUPPORTED_INTENTS}"
    ...

# ❌ Bad: Silent failure
def execute_skill(intent):
    if intent.action not in self.SUPPORTED_INTENTS:
        return  # Silent failure!
```

---

## 9. Measurable

**Principle**: What gets measured gets improved.

**What this means**:
- ✅ Latency metrics for all commands
- ✅ Success rate tracking
- ✅ User satisfaction surveys
- ✅ Accessibility compliance scoring
- ✅ Regular benchmarking
- ❌ Gut-feel improvements
- ❌ "Probably faster"

**Metrics to Track**:
- Intent recognition accuracy
- Skill execution success rate
- End-to-end latency (voice input to action)
- Network reliability
- User satisfaction per skill
- Accessibility audit scores

---

## 10. Accessibility is Quality, Not a Feature

**Principle**: Good design is accessible design.

**What this means**:
- ✅ A11y requirements in acceptance criteria
- ✅ A11y checklist before merge
- ✅ A11y testing in CI/CD
- ✅ User testing with actual disabled users
- ✅ Accessibility reviewed in every PR
- ❌ A11y as an afterthought
- ❌ "We'll fix accessibility later"
- ❌ Treating disabled users as edge cases

**Review Checklist**:
- [ ] Screen reader compatibility tested?
- [ ] Keyboard-only workflows work?
- [ ] Colors not sole differentiator?
- [ ] Latency acceptable for motor-impaired users?
- [ ] Error messages clear and spoken?
- [ ] Tested with actual users?

---

## 11. User Agency

**Principle**: Users must understand and be able to override Rocket's decisions.

**What this means**:
- ✅ Users see what command was understood
- ✅ Users can reject and rephrase
- ✅ Detailed logs of what happened
- ✅ Ability to define custom commands
- ✅ Keyboard shortcuts for frequent tasks
- ❌ Black-box automation
- ❌ Unpredictable behavior
- ❌ Inability to override system decisions

**Examples**:
```
User: "Send email"
System: "I'll send to john@example.com. OK?" (shows recipient)
User: "No, change to jane@example.com"
System: "Confirmed. Sending to jane@example.com now."
```

---

## 12. Documentation is Code

**Principle**: Undocumented code is unmaintainable code.

**What this means**:
- ✅ Every public method has docstring
- ✅ Complex algorithms have comments
- ✅ Usage examples provided
- ✅ Architecture decisions recorded in ADR (Architecture Decision Records)
- ✅ README for every component
- ❌ Assuming code is self-explanatory
- ❌ Comments that repeat code
- ❌ Documentation out of sync with code

**Documentation Standards**:
```python
def route_intent_to_skill(intent: Intent) -> Result:
    """
    Route an intent to the appropriate skill for execution.
    
    Args:
        intent: Parsed user intent with action and parameters
    
    Returns:
        Result object with status and execution details
    
    Raises:
        SkillNotFoundError: If no skill handles this intent
        
    Example:
        >>> intent = Intent(action="OPEN_APP", app="chrome")
        >>> result = route_intent_to_skill(intent)
        >>> print(result.status)
        "success"
    """
```

---

## Design Decision Recording

For significant decisions, create an ADR file:

```
docs/adr/ADR-001-custom-skills-plugin-system.md

# ADR 001: Custom Skills Plugin System

## Decision
We will use Python's `pluggy` library for skill registration instead of hardcoding skills.

## Rationale
- Allows users to write skills without modifying core code
- Makes testing easier (can mock skills)
- Future: Distribute skills as packages

## Alternatives Considered
1. Hardcoded skill registry - simpler initially but not extensible
2. Dynamic import of skill modules - less structured

## Consequences
- Small dependency on pluggy
- Skills need consistent interface
- Easier to maintain in long term
```

---

## Principle Conflicts

Sometimes principles conflict. **Resolution hierarchy**:

1. **Accessibility** (always trumps)
2. **Low Latency**
3. **Open Source**
4. **Modularity**
5. **Explicit Over Implicit**
6. **No Overengineering**

**Example**:
- Accessibility says: full logging (verbose)
- Low latency says: minimal logging (fast)
- **Resolution**: Always prioritize logging. Disable logging optionally for performance, but enable by default.
