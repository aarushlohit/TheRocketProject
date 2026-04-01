# Rocket: Accessibility-First Computer Automation

## Problem Statement

Users with visual impairments, motor impairments, and deaf-blind individuals face significant barriers to computer automation and control:

- **Screen readers** describe interfaces but don't enable control beyond standard keyboard/mouse
- **Voice assistants** are locked into proprietary ecosystems (Alexa, Google, Siri)
- **Motor-impaired users** struggle with precise clicking, typing, and navigation
- **Existing automation** (RPA, macro tools) is GUI-dependent and inaccessible
- **APIs and keyboard shortcuts** are inconsistent across applications

These users need a **universal, open-source, accessible automation system** that gives them control over *any* computer task.

---

## Why Rocket Matters

1. **Independence**: Users can automate complex workflows without sighted assistance
2. **Open-source**: No proprietary lock-in, full transparency for accessibility auditing
3. **Universal**: Works across applications, operating systems, and input methods
4. **Low-latency**: Real-time response to voice/drawing commands
5. **Modular**: New skills can be added without modifying core
6. **Accessible to build**: The toolchain itself must be accessible to contributors

---

## Target Users

### Primary
- Blind users (need accessible input + universal automation)
- Deaf-blind users (multimodal input: drawing + haptic feedback)
- Motor-impaired users (voice commands, gesture-based drawing)

### Secondary
- Power users who prefer voice/drawing over mouse
- Developers building custom automation
- Accessibility advocates building similar systems

### Not Intended For
- Users needing real-time gaming automation
- Users needing cloud-based cross-device sync (Phase 2+)

---

## Real-World Scenarios

### Scenario 1: Bank Account Access
**User**: Blind professional managing personal finances

**Without Rocket**: 
- Navigate bank website with screen reader
- Find login button (inconsistently labeled)
- Locate transfer button within cluttered UI
- Navigate dropdown menus for account selection
- Risk mis-tapping due to screen reader pagination

**With Rocket**:
```
"Go to banksite.com, select my checking account, transfer 500 to savings"
```
Rocket handles navigation, form filling, and verification.

### Scenario 2: Email Triage
**User**: Motor-impaired user with limited fine motor control

**Without Rocket**:
- Move mouse to email folders
- Perform precise clicks on small UI elements
- Risk missing target due to tremor

**With Rocket**:
```
*draws path upward* → interpreted as "move mail to folder"
*draws rectangular lasso* → selects multiple emails
```

### Scenario 3: Complex Workflow
**User**: Deaf-blind data analyst

**Without Rocket**:
- Cannot use standard keyboard shortcuts (too many to memorize)
- Cannot see visual feedback of actions
- Inefficient screen reader navigation for repetitive tasks

**With Rocket**:
```
"Open spreadsheet, filter by June, pivot by region, export to CSV"
```
Rocket chains skills, provides haptic confirmation at each step.

---

## Unique Aspects

| Aspect | Rocket | Traditional Assistants | RPA Tools | Accessibility Tools |
|--------|--------|------------------------|-----------|---------------------|
| **Open Source** | ✅ | ❌ | Partial | ✅ |
| **Voice Input** | ✅ (Whisper) | ✅ (Proprietary) | ❌ | Partial |
| **Drawing Input** | ✅ (OCR) | ❌ | ❌ | ❌ |
| **Accessible Setup** | ✅ (Goal) | ❌ | ❌ | ❌ |
| **Works Offline** | ✅ | ❌ | ✅ | ✅ |
| **Cross-platform** | ✅ (Goal) | Partial | Partial | Partial |
| **Skill Extensibility** | ✅ | Limited | ✅ | Limited |

---

## Success Metrics (Long-Term)

- **Usability**: Blind users can complete a 10-step workflow in <2 minutes
- **Reliability**: 99% command success rate (no failed automations)
- **Latency**: <500ms response time from voice/drawing input to action
- **Community**: 100+ custom skills contributed by users
- **Accessibility**: Full A11y compliance for development tools
- **Platform coverage**: Windows, macOS, Linux, iOS, Android

---

## Not In Scope (Yet)

- Cloud sync across devices
- AI-powered task prediction
- Real-time visual feedback (depends on accessibility UI progress)
- Integration with proprietary assistants (Alexa, Google, Siri plugins)
- Browser extension ecosystem (Phase 2)
- Mobile automation (Phase 2)

---

## Connection to Broader Movement

Rocket is part of a growing acknowledgment that **automation is an accessibility tool**, not just a convenience feature. Similar to how JAWS (screen reader) revolutionized computer access for blind users, Rocket aims to revolutionize automation access.
