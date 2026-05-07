---
name: mutation-hardening
description: >
  Mutation hardening loop for Java projects using PITest. Use this skill whenever
  you finish implementing or modifying Java code and want to verify the tests are
  actually meaningful — not just covering lines but truly detecting bugs. Also use
  when the user says "harden the tests", "run mutation tests", "pitest", "mutation
  score", "kill mutants", "are my tests good enough?", or after completing any
  non-trivial Java feature/bugfix. The skill configures PITest if absent, runs it,
  reads survived mutants, writes targeted tests to kill them, and loops until the
  mutation score hits the target or no more viable mutants remain.
---

# Mutation Hardening Loop

A test-quality enforcement loop: inject faults, see which ones your suite misses,
write the missing tests, repeat. When this loop converges, every meaningful
code path has at least one assertion that would catch a regression.

**Bundled resources:**
- `references/pitest-config.md` — Maven/Gradle setup snippets for JUnit 5/4 + Java 17/21
- `scripts/parse_mutations.py` — parses `mutations.xml`, prints worklist of SURVIVED + NO_COVERAGE mutants grouped by class/method, and computes test_strength + mutation_coverage. Use this in Phase 3 instead of writing ad-hoc XML parsing.

---

## When to run

- After finishing a feature or bugfix that has unit tests
- When asked to "make sure tests are solid", "harden", "mutation test", or "pitest"
- Before marking a task complete on critical business logic

Do NOT run on:
- Projects with no unit tests at all (add tests first)
- Pure integration/E2E test suites

---

## Phase 0 — Detect Project

```
1. Check for pom.xml → Maven
2. Check for build.gradle / build.gradle.kts → Gradle
3. Identify test framework: look for junit-jupiter/junit5 vs junit:junit (JUnit 4) vs testng
4. Identify Java version: check <java.version> in pom.xml or sourceCompatibility in build.gradle
```

Set variables for later:
- `BUILD_TOOL` = maven | gradle
- `TEST_FRAMEWORK` = junit5 | junit4 | testng
- `JAVA_VERSION` = 11 | 17 | 21 | …
- `REPORT_DIR` = `target/pit-reports` (Maven) or `build/reports/pitest` (Gradle)

---

## Phase 1 — Configure PITest

Check if PITest plugin is already configured.

**Maven**: search `pom.xml` for `pitest-maven` in `<build><plugins>`. If absent, add it.
**Gradle**: search `build.gradle` for `info.solidsoft.pitest`. If absent, add it.

Use the config from `references/pitest-config.md` for your BUILD_TOOL and TEST_FRAMEWORK.

**Critical defaults to enforce:**
- Exclude integration tests: `*IT`, `*IntegrationTest`, `*E2ETest` (and any class using `@SpringBootTest`, **`@QuarkusTest` / full Quarkus bootstrap**, or Testcontainers)
- `avoidCallsTo`: `java.util.logging`, `org.slf4j`, `org.apache.log4j` (suppress log mutation noise)
- `outputFormats`: `XML,HTML` (need XML for parsing, HTML for human review)
- `threads`: 4 (reasonable default; bump to match CPU count on CI)
- **Maven + PIT 1.23+**: add `pitest-history-plugin` to `pitest-maven` plugin dependencies; set `historyInputFile` and `historyOutputFile` to the same path under `${project.build.directory}` (for example `target/pitest-history.bin`). Gradle projects typically configure `withHistory` / history files via the Solidsoft plugin — see `references/pitest-config.md`.
- For JUnit 5 + Maven: add `pitest-junit5-plugin` dependency inside the plugin config
- For JUnit 5 + Gradle: set `testPlugin = 'junit5'`

**Mutator group (`DEFAULTS` vs `STRONGER`):**
- Start with **`DEFAULTS`** (PITest default stable set).
- Use **`STRONGER`** when you want stricter checks; it adds mutators such as **`RemoveConditionals` (`EQUAL_IF`)** and others, which often surface **new SURVIVED** mutants until tests assert both branches and concrete values (not only exception type).
- Avoid **`ALL`** (officially discouraged in the PITest FAQ).

---

## Phase 2 — Run Mutation Tests

**Maven** (see `references/pitest-config.md` for a **1.23.1** baseline including `pitest-history-plugin`):
```bash
mvn test-compile pitest:mutationCoverage -Dsurefire.failIfNoSpecifiedTests=false
```
Use `./mvnw` instead of `mvn` when the project provides the Maven Wrapper.

**Gradle:**
```bash
./gradlew pitest
```

The run will:
1. Execute the full unit test suite first (must be green — if not, fix failing tests before proceeding)
2. Generate mutants and run only relevant tests per mutant
3. Write report to `$REPORT_DIR/`

**If the run fails with "Tests did not pass without mutation":**
- Test suite itself broken. Fix failing tests first. Do not proceed with mutation.
- **Verify by running target tests standalone first** (`mvn test -Dtest=YourTestClass`). If green standalone but red under PITest, it's a config mismatch.
- Common causes:
  - Config mismatch between Surefire and PITest (excluded tests in Surefire not excluded in PITest config)
  - Test depends on **Spring** or **Quarkus** application context that PITest's forked minion does not bootstrap the same way as Surefire (see **Quarkus / CDI** below)
  - Test relies on system properties or env vars not propagated to forked PITest JVM
  - **JaCoCo `prepare-agent`** injecting `argLine`: PITest may merge that into child JVM args; if you see odd failures, try **`mvn ... -Djacoco.skip=true`** for the mutation goal only (keep JaCoCo for normal `mvn test`).

### Quarkus / CDI full-stack tests

Classes annotated with **`@QuarkusTest`** (and similar tests that start the full Quarkus runtime) often **pass under Surefire** but **fail under PITest** during coverage pre-scan (*"did not pass without mutation"* for the whole class).

**Recommended handling:**
- **Do not** put those classes in PITest `targetTests`; keep verifying them with **`mvn test`** / Failsafe.
- Restrict PITest to **fast unit tests** (pure JUnit + mocks) and, if needed, a narrow `targetClasses` package that those tests actually exercise.
- Document in the project why integration tests are excluded from mutation scope.

### Incremental history (Maven, PIT 1.23+)

With **`pitest-history-plugin`** and matching **`historyInputFile` / `historyOutputFile`**, PITest **reuses** results for unchanged code. This is **expected and desirable** (faster CI and local runs).

You may see log lines such as **"Incremental analysis reduced number of mutations"** or **"Ran 0 tests"** for mutants skipped via history — **not** a misconfiguration.

**Do not** delete the history file as part of the normal loop. Only remove **`pitest-history.bin`** (or equivalent) when you intentionally need a **full recompute** (e.g. after changing the **mutator group**, major refactor, or debugging suspected stale history).

**Typical runtime:** 1–5 min for small projects, 10–30 min for large ones.
Wait for completion before proceeding.

---

## Phase 3 — Parse Results

**Use the bundled script** to avoid writing XML parsing yourself:

```bash
python3 <skill-dir>/scripts/parse_mutations.py $REPORT_DIR/mutations.xml
```

The script prints a worklist grouped by class+method (covering both Phase 5a and 5b), computes both metrics, and exits 0 only if both targets are met (handy as a CI gate). Pass `--json` for machine-readable output you can pipe into other tools.

If you need raw access (rare), the XML structure is — for each `<mutation>` element, extract:
- `status` — KILLED | SURVIVED | NO_COVERAGE | TIMED_OUT | NON_VIABLE
- `mutatedClass` — fully qualified class name
- `mutatedMethod` — method name
- `lineNumber` — source line
- `mutator` — the operator that was applied
- `description` — human-readable description of the mutation

**Two distinct problems require two distinct fixes:**

- `SURVIVED` → **assertion gap**: code is executed but no assertion catches the mutation. Fix by writing targeted assertions (Phase 5).
- `NO_COVERAGE` → **coverage gap**: code is never executed by any unit test. Fix by writing tests that *call* the uncovered method/branch.

Both contribute to the overall quality picture. Track them separately:

```
test_strength      = KILLED / (KILLED + SURVIVED)             ← assertion quality
mutation_coverage  = KILLED / (KILLED + SURVIVED + NO_COVERAGE + TIMED_OUT)  ← overall harness
```

**Targets:**
- `test_strength >= 0.80` — assertions are doing their job
- `mutation_coverage >= 0.70` — most code is reached by tests

**Common pattern**: `test_strength = 100%` with `mutation_coverage = 50%` means existing tests are excellent but several methods have *zero* unit tests. Don't celebrate — there's a real gap. Group the NO_COVERAGE mutants by method and prioritize methods with the most uncovered mutants (highest leverage).

Ignore TIMED_OUT, NON_VIABLE, KILLED for the worklist.

Group survived mutants by class and method for efficient test writing.

---

## Phase 4 — Analyze Survived Mutants

For each survived mutant, understand what it means and what test would kill it.

### Mutator cheat sheet

| Mutator | What changed | Test to kill it |
|---------|-------------|-----------------|
| `ConditionalsBoundary` | `>=` → `>` (or similar) | Test the exact boundary value: `x == threshold` |
| `NegateConditionals` | `==` → `!=` (or similar) | Test both the true and false branch |
| `Math` | `+` → `-` (or similar) | Assert the exact numeric result of the operation |
| `Increments` | `i++` → `i--` | Assert loop count or final accumulator value |
| `InvertNegatives` | `-x` → `x` | Test with negative input, assert sign of result |
| `VoidMethodCall` | removed call to void method | Verify the side effect of that method (state change, mock verify, etc.) |
| `EmptyReturns` | returned `""` / `Optional.empty()` / `[]` instead of real value | Assert the return value is not empty |
| `NullReturns` | returned `null` instead of object | Assert return value is not null |
| `FalseReturns` / `TrueReturns` | flipped boolean return | Assert both true and false return paths |
| `PrimitiveReturns` | returned `0` instead of real value | Assert the actual numeric return value |
| `RemoveConditionalMutator_EQUAL_IF` / `EQUAL_ELSE` | conditional removed (often `== null` / `!= null`) | Cover **both** branches with assertions on **observable outcome** (return value, field, message text, etc.) — not only `assertThrows(SameException.class)` |

**STRONGER** enables **`RemoveConditionals` (`EQUAL_IF`)** in addition to the `EQUAL_ELSE` case included in **DEFAULTS**. Expect more survivors on null-guards until tests distinguish branches.

### Equivalent mutants (do NOT write a test for these)

A mutant is likely equivalent when:
- The mutated line is in dead code that can never be reached
- The mutation changes a constant in a way that is mathematically indistinguishable (e.g., `int i = 2; if(i >= 1)` mutated to `if(i > 1)` — always the same result)
- The mutated method is `toString()`, `hashCode()`, or logging-only code

Document equivalent mutants in a comment in the test file. Do not count them against the score.

---

## Phase 5 — Write Targeted Tests

### 5a. NO_COVERAGE methods (write tests that exercise the code)

Group NO_COVERAGE mutants by method. For each uncovered method:
1. Read the method to understand inputs, outputs, branches
2. Write tests that call the method with realistic inputs covering each branch the mutants point to
3. Each test must assert on a meaningful return value or side effect — not just `assertNotNull`
4. After Phase 5a, NO_COVERAGE mutants flip to KILLED or SURVIVED. Survived ones move to 5b.

### 5b. SURVIVED mutants (strengthen assertions)

For each survived mutant (skip equivalents):

1. Read the source file to understand the method context — what it does, what inputs it accepts
2. Identify the specific behavior the mutant exploits (boundary, arithmetic result, null check, side effect)
3. Write a test that:
   - Has a descriptive name: `methodName_whenBoundaryCondition_thenExpectedResult`
   - Sets up inputs that hit the exact line the mutant is on
   - Has a concrete assertion on the value/behavior the mutant changes
   - Is a fast unit test (no Spring context, no DB, mock dependencies)

**Group related tests**: if 3 survived mutants are all in the same method, write them in one test class rather than 3 separate files.

**Do not write junk tests**: a test that asserts `assertNotNull(result)` when the mutant is a `ConditionalsBoundary` on a comparator does not kill the mutant. Think about what the mutant actually changed.

**Example — ConditionalsBoundary on `approve(int amount)`:**
```java
// Original: if (amount >= LIMIT) throw new LimitExceededException();
// Mutant:   if (amount >  LIMIT) throw new LimitExceededException();
// Surviving because no test passes amount == LIMIT

@Test
void approve_whenAmountEqualsLimit_thenThrowsLimitExceeded() {
    assertThrows(LimitExceededException.class, () -> service.approve(LIMIT));
}

@Test
void approve_whenAmountOneLessThanLimit_thenNoException() {
    assertDoesNotThrow(() -> service.approve(LIMIT - 1));
}
```

---

## Phase 6 — Re-run and Verify

After writing tests:

1. Run the unit test suite to confirm all new tests pass (don't run PITest yet if something's broken)
2. Re-run PITest (Phase 2)
3. Re-parse results (Phase 3)
4. Compute new test_strength

If test_strength improved: good. Check if >= 0.80.
If a "new" survived mutant appeared that wasn't there before: investigate — you may have accidentally broken test isolation.

---

## Phase 7 — Loop or Stop

**Stop when any of these is true:**
- `test_strength >= 0.80`
- All remaining survived mutants are confirmed equivalent (documented)
- You've done 3 iterations with no improvement (investigate why — maybe the config is wrong)

**If stuck below 0.80 after 2 iterations:**
- Re-read the survived mutant list with fresh eyes
- Check if `avoidCallsTo` is filtering too aggressively
- Check if some mutants are on generated code (Lombok, MapStruct) — exclude those classes

**Report to the user:**
```
Mutation Hardening Complete
──────────────────────────
Test Strength:  87% (▲ from 61%)
Killed:         142 / 163 covered mutants
Survived:       21 mutants → 18 killed in this session, 3 confirmed equivalent
New tests added: 14 (in OrderServiceTest, PaymentValidatorTest)
Equivalent mutants documented: 3 (in toString/logging methods)
```

---

## Quick reference

- PITest docs: https://pitest.org/quickstart/
- Maven plugin: https://pitest.org/quickstart/maven/
- Gradle plugin: https://gradle-pitest-plugin.solidsoft.info/
- Arcmutate (advanced mutators): https://docs.arcmutate.com/
- Report location: `target/pit-reports/` (Maven) or `build/reports/pitest/` (Gradle)
