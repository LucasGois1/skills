# PITest Configuration Reference

## Maven — JUnit 5 (baseline for PIT **1.23.1**)

Example **`pitest-maven`** setup: **1.23.1**, **pitest-junit5-plugin 1.2.3**, **pitest-history-plugin 0.0.1** (incremental history on Maven requires this plugin from PIT **1.23+**), optional `${pitest.*}` thresholds, and **`--add-opens`** for Java **17+**.

Replace every `com.example.app` prefix below with **your application’s root package**. Adjust `excludedClasses` / `excludedTestClasses` to match your layout (Spring Boot, layered packages, generated code, etc.).

**`<properties>`** (example: warn-only defaults; CI can enforce via `-Dpitest.mutationThreshold=…`):

```xml
<pitest.mutationThreshold>0</pitest.mutationThreshold>
<pitest.coverageThreshold>0</pitest.coverageThreshold>
```

**`<build><plugins>`**:

```xml
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.23.1</version>
    <dependencies>
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-junit5-plugin</artifactId>
            <version>1.2.3</version>
        </dependency>
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-history-plugin</artifactId>
            <version>0.0.1</version>
        </dependency>
    </dependencies>
    <configuration>
        <targetClasses>
            <param>com.example.app.*</param>
        </targetClasses>
        <targetTests>
            <param>com.example.app.*</param>
        </targetTests>
        <excludedClasses>
            <param>com.example.app.*.dto.*</param>
            <param>com.example.app.*.config.*</param>
            <param>com.example.app.*.exception*.*</param>
            <param>com.example.app.*.exceptions.*</param>
            <param>com.example.app.Application</param>
            <param>*MapperImpl</param>
            <param>*$$*</param>
        </excludedClasses>
        <excludedTestClasses>
            <param>*IT</param>
            <param>*IntegrationTest</param>
            <param>*TestIT</param>
            <param>*E2ETest</param>
            <param>*MockMvcTest</param>
        </excludedTestClasses>
        <avoidCallsTo>
            <avoidCallsTo>java.util.logging</avoidCallsTo>
            <avoidCallsTo>org.slf4j</avoidCallsTo>
            <avoidCallsTo>org.apache.log4j</avoidCallsTo>
            <avoidCallsTo>org.apache.commons.logging</avoidCallsTo>
        </avoidCallsTo>
        <outputFormats>
            <outputFormat>XML</outputFormat>
            <outputFormat>HTML</outputFormat>
        </outputFormats>
        <threads>4</threads>
        <mutators>
            <mutator>DEFAULTS</mutator>
        </mutators>
        <timestampedReports>false</timestampedReports>
        <historyInputFile>${project.build.directory}/pitest-history.bin</historyInputFile>
        <historyOutputFile>${project.build.directory}/pitest-history.bin</historyOutputFile>
        <mutationThreshold>${pitest.mutationThreshold}</mutationThreshold>
        <coverageThreshold>${pitest.coverageThreshold}</coverageThreshold>
        <jvmArgs>
            <jvmArg>--add-opens=java.base/java.lang=ALL-UNNAMED</jvmArg>
            <jvmArg>--add-opens=java.base/java.util=ALL-UNNAMED</jvmArg>
        </jvmArgs>
    </configuration>
</plugin>
```

Run:

```bash
mvn test-compile pitest:mutationCoverage -Dsurefire.failIfNoSpecifiedTests=false
```

If the repository includes a Maven Wrapper, use `./mvnw` instead of `mvn`.

Scoped run (override targets without editing `pom.xml`):

```bash
mvn test-compile pitest:mutationCoverage \
  -Dpitest.targetClasses=com.example.app.order.OrderService \
  -Dpitest.targetTests=com.example.app.order.OrderServiceTest \
  -Dsurefire.failIfNoSpecifiedTests=false
```

From **PIT 1.23+**, incremental analysis on **Maven** requires **`pitest-history-plugin`** on the `pitest-maven` plugin classpath, plus matching `historyInputFile` / `historyOutputFile`. See [incremental analysis](https://pitest.org/quickstart/incremental_analysis/).

---

## Maven — JUnit 4

Same as above but **remove** the `pitest-junit5-plugin` dependency. JUnit 4 is natively supported.

---

## Gradle — JUnit 5 (Kotlin DSL)

In `build.gradle.kts`:

```kotlin
plugins {
    id("info.solidsoft.pitest") version "1.15.0"
}

pitest {
    junit5PluginVersion = "1.2.1"
    testPlugin = "junit5"
    targetClasses = setOf("com.example.*")  // adjust to your base package
    targetTests = setOf("com.example.*")
    excludedTestClasses = setOf("*IT", "*IntegrationTest", "*E2ETest")
    avoidCallsTo = setOf(
        "java.util.logging",
        "org.slf4j",
        "org.apache.log4j",
        "org.apache.commons.logging"
    )
    outputFormats = setOf("XML", "HTML")
    threads = 4
    withHistory = true
    historyInputFile = file("${buildDir}/pitest-history.bin")
    historyOutputFile = file("${buildDir}/pitest-history.bin")
    mutators = setOf("DEFAULTS")
    timestampedReports = false
}
```

In `build.gradle.kts`, also add the plugin dependency to buildscript if needed:
```kotlin
buildscript {
    repositories { mavenCentral() }
    dependencies {
        classpath("info.solidsoft.gradle.pitest:gradle-pitest-plugin:1.15.0")
    }
}
```

Run:
```bash
./gradlew pitest
```

---

## Gradle — JUnit 5 (Groovy DSL)

In `build.gradle`:

```groovy
plugins {
    id 'info.solidsoft.pitest' version '1.15.0'
}

pitest {
    junit5PluginVersion = '1.2.1'
    testPlugin = 'junit5'
    targetClasses = ['com.example.*']
    targetTests = ['com.example.*']
    excludedTestClasses = ['*IT', '*IntegrationTest', '*E2ETest']
    avoidCallsTo = ['java.util.logging', 'org.slf4j', 'org.apache.log4j']
    outputFormats = ['XML', 'HTML']
    threads = 4
    withHistory = true
    mutators = ['DEFAULTS']
    timestampedReports = false
}
```

---

## Excluding Generated Code (Lombok, MapStruct)

Add classes that are auto-generated — no point mutating them:

```xml
<!-- Maven -->
<excludedClasses>
    <param>*MapperImpl</param>
    <param>*_.class</param>  <!-- JPA metamodel -->
</excludedClasses>
```

```kotlin
// Gradle Kotlin DSL
excludedClasses = setOf("*MapperImpl", "*_")
```

---

## Stronger Mutators (optional, more thorough)

Replace `DEFAULTS` with `STRONGER` for more aggressive testing. Expect ~30% more mutants and longer runs:

```xml
<mutators>STRONGER</mutators>
```

Or add specific advanced mutators on top of defaults:
```xml
<mutators>
    <mutator>DEFAULTS</mutator>
    <mutator>CONSTRUCTOR_CALLS</mutator>
    <mutator>NON_VOID_METHOD_CALLS</mutator>
</mutators>
```

---

## Multi-module Maven (aggregate report)

In the parent `pom.xml`, add `pitest-maven` with goal `report-aggregate`:

```xml
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.16.1</version>
    <executions>
        <execution>
            <id>aggregate</id>
            <goals><goal>report-aggregate</goal></goals>
            <phase>verify</phase>
        </execution>
    </executions>
</plugin>
```

Run from parent: `mvn verify -Pprepare-agent`

---

## Report Locations

| Build tool | Location |
|------------|----------|
| Maven      | `target/pit-reports/mutations.xml` and `target/pit-reports/index.html` |
| Gradle     | `build/reports/pitest/mutations.xml` and `build/reports/pitest/index.html` |

With `timestampedReports=false`, the report always overwrites the same directory (easier to script).

---

## Java 17+ Module System Issues

If you see `InaccessibleObjectException` or similar module errors under PITest, add `jvmArgs` under `pitest-maven` `<configuration>` (included in the Maven JUnit 5 baseline above):

```xml
<jvmArgs>
    <jvmArg>--add-opens=java.base/java.lang=ALL-UNNAMED</jvmArg>
    <jvmArg>--add-opens=java.base/java.util=ALL-UNNAMED</jvmArg>
</jvmArgs>
```

```kotlin
// Gradle Kotlin DSL
jvmArgs = listOf(
    "--add-opens=java.base/java.lang=ALL-UNNAMED",
    "--add-opens=java.base/java.util=ALL-UNNAMED"
)
```
