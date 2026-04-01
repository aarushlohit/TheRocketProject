# Rocket Development Roadmap

## Overall Strategy

```
Phase 0: Foundation (NOW)
  ↓ (3-4 months)
Phase 1: Stabilization (Core works everywhere)
  ↓ (3-4 months)
Phase 2: Expansion (More skills, more platforms)
  ↓ (6+ months)
Phase 3+: Advanced (Learning, federation, cross-device)
```

---

## Phase 0: Foundation (Months 1-4)

**Goal**: Build a clean, stable foundation with core skills working.

**Definition of Done**:
- ✅ Blind user can open app and type text via voice
- ✅ Motor-impaired user can navigate editor via drawing gestures
- ✅ Offline-first with local STT/OCR
- ✅ < 800ms latency on deterministic commands
- ✅ All code documented and tested

### Phase 0 Milestones

#### M0.1: Repository Setup & Docs (Week 1-2)
**Deliverables**:
- [x] Complete repository structure
- [x] All documentation complete
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Accessibility checklist for development
- [ ] Contribution guidelines

**Tasks**:
- [ ] Create base.yaml GitHub Actions config
- [ ] Set up pre-commit hooks (black, ruff, mypy)
- [ ] Configure pytest with coverage thresholds
- [ ] Create PR template with accessibility checklist

#### M0.2: Backend Skeleton (Week 2-3)
**Deliverables**:
- [ ] Agent main.py with WebSocket server
- [ ] Intent/Result data structures
- [ ] BaseSkill abstract class
- [ ] Platform adapters (Windows, macOS, Linux)
- [ ] Basic NLU engine (rule-based)
- [ ] Logging infrastructure

**Tasks**:
- [ ] Set up Python 3.11 environment with dependencies
- [ ] Implement Agent class
- [ ] Implement WebSocket server (handle connections, message routing)
- [ ] Test with wscat or similar

#### M0.3: Core Skills (Week 3-5)
**Deliverables**:
- [ ] OPEN_APP skill
- [ ] TYPE_TEXT skill
- [ ] PRESS_KEYS skill
- [ ] SCROLL skill
- [ ] CLICK skill
- [ ] OPEN_URL skill

**Tasks**:
- [ ] Implement each skill on all platforms
- [ ] Platform adapter tests (mocked)
- [ ] Integration tests for each skill
- [ ] Latency benchmarks

**Latency Target**: < 1s for each skill

#### M0.4: Local AI Setup (Week 4-5)
**Deliverables**:
- [ ] Whisper integration (local or cloud fallback)
- [ ] Gesture recognition (rule-based)
- [ ] Model download script
- [ ] Documentation for setup

**Tasks**:
- [ ] Integrate whisper-python
- [ ] Create models/ directory structure
- [ ] Write gesture recognizer (upward/downward/etc)
- [ ] Model auto-download on first run

#### M0.5: Mobile Prototype (Week 3-5, in parallel)
**Deliverables**:
- [ ] Flutter app skeleton
- [ ] Voice input capture
- [ ] Drawing input capture
- [ ] WebSocket client
- [ ] Haptic feedback module
- [ ] Connection to desktop agent

**Tasks**:
- [ ] Flutter new project
- [ ] speech_to_text integration
- [ ] touch gesture capture
- [ ] websocket_channel setup
- [ ] Test with agent running locally

#### M0.6: Integration Testing (Week 5-6)
**Deliverables**:
- [ ] E2E tests: Voice command → Action
- [ ] E2E tests: Drawing gesture → Action
- [ ] Latency measurements
- [ ] User testing with accessibility users

**Tasks**:
- [ ] Test with real users (blind/motor-impaired)
- [ ] Accessibility audit of mobile app
- [ ] Accessibility audit of backend
- [ ] Document issues and improvements

#### M0.7: Polish & Docs (Week 6-7)
**Deliverables**:
- [ ] Final documentation
- [ ] Setup guide for developers
- [ ] Setup guide for end users
- [ ] Demo video (accessible captions + audio description)
- [ ] Contribution guide

**Tasks**:
- [ ] Complete all docs
- [ ] Create setup.py / pyproject.toml
- [ ] Create requirements.txt
- [ ] Test fresh install from scratch

#### M0.8: Release (Week 7-8)
**Deliverables**:
- [ ] v0.1.0 release
- [ ] GitHub release notes
- [ ] Setup instructions in README
- [ ] Demo accessible to disabled users

---

## Phase 1: Stabilization (Months 5-8)

**Goal**: Make core system reliable, well-tested, multi-platform.

**Definition of Done**:
- ✅ 95%+ success rate on demo skills
- ✅ Fully working on Windows, macOS, Linux
- ✅ Full test coverage (> 80%)
- ✅ Comprehensive error handling
- ✅ User feedback integration

### Phase 1 Milestones

#### M1.1: Testing & Robustness (Weeks 1-2)
- [ ] 100% unit test coverage for skills
- [ ] Integration test coverage
- [ ] Platform-specific testing (VM + real machines)
- [ ] Error injection testing
- [ ] Network failure recovery

#### M1.2: Performance Optimization (Weeks 2-3)
- [ ] Profiling with py-spy
- [ ] Identify bottlenecks
- [ ] Latency targets: < 500ms for voice, < 300ms for drawing
- [ ] Model loading optimization

#### M1.3: Documentation Improvements (Weeks 3-4)
- [ ] Architecture Decision Records (ADRs) for all major decisions
- [ ] API documentation (generated from code)
- [ ] Troubleshooting guide
- [ ] FAQ for common issues

#### M1.4: Developer Experience (Weeks 4-5)
- [ ] Simplified onboarding
- [ ] Local development guide
- [ ] Debugging guide (logging, breakpoints)
- [ ] Contributing guide with first-timer issues

#### M1.5: Accessibility Hardening (Weeks 5-7)
- [ ] Screen reader testing (NVDA, JAWS, VoiceOver)
- [ ] Motor-disabled user testing
- [ ] Deaf-blind user testing (haptic feedback)
- [ ] Fix issues found in testing

#### M1.6: Polish & Release (Weeks 7-8)
- [ ] v0.2.0 release (stable)
- [ ] Backward compatibility from v0.1.0
- [ ] Deprecation guide if any API changes

---

## Phase 2: Feature Expansion (Months 9-16)

**Goal**: Expand skill set, add new input methods, improve UX.

### Phase 2a: More Skills (First Half)

#### New Skills to Add
- [ ] SELECT_TEXT (select word/line/all)
- [ ] SEARCH_WEB (Google/Bing integration)
- [ ] READ_SCREEN (TTS for visible text)
- [ ] SMART_CLICK_BY_TEXT (OCR-based clicking)
- [ ] SWITCH_APP (focus open windows)
- [ ] SEND_EMAIL (Gmail API integration - optional)

#### Latency Target
- [ ] All skills < 1s for user feedback

#### Testing
- [ ] User acceptance testing
- [ ] Real-world workflow testing

### Phase 2b: Accessibility Enhancements

- [ ] Mobile app: Improved a11y (VoiceOver/TalkBack)
- [ ] Backend: More descriptive error messages
- [ ] Braille input support (Phase 2, optional)
- [ ] Visual feedback options for assistive tech

### Phase 2c: Mobile App Maturity

- [ ] Better gesture recognition (ML model? Or stay rule-based?)
- [ ] Offline mode (queue commands locally)
- [ ] Custom vocabulary (user-defined commands)
- [ ] Skill discovery in app
- [ ] Connection UI improvements

---

## Phase 3: Advanced Features (Months 17+)

### Phase 3a: Learning & Customization

- [ ] User can create custom skills via voice/UI
- [ ] System learns common automation sequences
- [ ] Macro recording: "Remember this sequence"
- [ ] Custom voice commands per user

### Phase 3b: Cross-Device Features

- [ ] Cloud sync of config/preferences (optional)
- [ ] Multi-device support (home automation, mobile, desktop)
- [ ] Distributed skill execution
- [ ] State synchronization

### Phase 3c: Advanced Input

- [ ] Eye-tracking input (if hardware available)
- [ ] Brain-computer interface research (future)
- [ ] Predictive text/actions based on context
- [ ] Ambient audio recognition

### Phase 3d: Enterprise & Ecosystem

- [ ] Custom skill marketplace
- [ ] Team collaboration features
- [ ] Audit logs for compliance
- [ ] Enterprise deployment guides

---

## Parallel Workstreams

### Developer Relations (Throughout)
- [ ] Blog posts about design decisions
- [ ] Conference talks (accessibility + automation)
- [ ] Community forums/Discord
- [ ] User testimonials from disabled users

### Accessibility Research (Throughout)
- [ ] Regular user testing with real users
- [ ] Collaboration with disability organizations
- [ ] WCAG/ATAG compliance documentation
- [ ] Accessibility guidelines for skill developers

### Testing & QA (Throughout)
- [ ] Automated testing at each phase
- [ ] Manual accessibility testing
- [ ] Real user validation
- [ ] Performance benchmarking

---

## Resource Allocation (Estimated)

### Phase 0 (Foundation)
**Effort**: 4-6 person-months

| Role | Effort | Notes |
|------|--------|-------|
| Backend Lead | 3 months | Core agent, skills, architecture |
| Mobile Lead | 2.5 months | Flutter app, WebSocket client |
| DevOps/Infra | 1 month | CI/CD, testing setup |
| Accessibility Lead | 1 month | User testing, standards |
| Documentation | 1 month | All docs, guides |

**Total**: ~8.5 person-months for 4-month timeline (need parallelization)

### Phase 1 (Stabilization)
**Effort**: 2-3 person-months

### Phase 2 (Expansion)
**Effort**: 3-4 person-months

---

## Success Metrics

### Phase 0
- [ ] 6+ core skills working reliably
- [ ] < 800ms latency on voice commands
- [ ] < 500ms latency on drawing gestures
- [ ] 95%+ command success rate
- [ ] Positive feedback from accessibility users

### Phase 1
- [ ] 95%+ unit test coverage
- [ ] Working on 3 platforms (Windows, macOS, Linux)
- [ ] 10+ skills with good documentation
- [ ] < 100ms latency for drawing gestures
- [ ] Community contributions accepted

### Phase 2
- [ ] 30+ skills available
- [ ] Mobile app on app stores (Google Play, Apple App Store)
- [ ] 1000+ GitHub stars
- [ ] Positive press from accessibility community

### Phase 3+
- [ ] 100+ skills (community + official)
- [ ] Estimated 10,000+ users
- [ ] Corporate partnerships (accessibility orgs)
- [ ] Sustainable funding model

---

## Risk Mitigation

### Technology Risks
- **Latency too high**: Start with rule-based NLU, optimize before Phase 1
- **Platform fragmentation**: Test on real hardware, not just VMs
- **Model availability**: Host models ourselves, don't rely on cloud downloads

### Market Risks
- **Low adoption**: Build WITH disability communities, not FOR them
- **Competition**: Focus on accessibility innovation, not general automation
- **Economic**: Open-source sustainable via grants, donations, not VC

### Team Risks
- **Burnout**: Phase tasks carefully, allow iteration
- **Contributor churn**: Document everything, make contributions easy
- **Knowledge silos**: Pair programming, good documentation

---

## Decision Checkpoints

### End of Phase 0
**Questions**:
- Does system meet latency requirements?
- Are users satisfied with MVP?
- Are skills reliable enough?
- Should Phase 1 proceed or pivot?

**Go/No-Go Decision**: Community feedback drives this

### End of Phase 1
**Questions**:
- Is system production-ready?
- Is platform support solid?
- Is test coverage sufficient?
- Should SDK be released for community skills?

**Go/No-Go Decision**: Stability metrics drive this

### End of Phase 2
**Questions**:
- Has adoption reached target?
- Are community skills ecosystem healthy?
- Is accessibility maintained as features grow?
- Should enterprise version be considered?

**Go/No-Go Decision**: Adoption and feedback drive this

---

## Long-Term Vision (5+ Years)

**Rocket becomes the standard way disabled users automate computers.**

- [ ] Available on all major platforms
- [ ] 100,000+ users with diverse disabilities
- [ ] Thriving skill marketplace
- [ ] Academic research platform for accessibility
- [ ] Influencing industry accessibility standards
- [ ] Sustainable funding model (grants, donations, enterprise)
- [ ] Non-profit governance model

**Success = Rocket becomes boring (so everyone uses it).**
