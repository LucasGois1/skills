# PITest Configuration Reference

## Maven — JUnit 5

Add inside `<build><plugins>` in `pom.xml`:

```xml
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.16.1</version>
    <dependencies>
        <!-- Required for JUnit 5 support -->
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-junit5-plugin</artifactId>
            <version>1.2.1</version>
        </dependency>
    </dependencies>
    <configuration>
        <targetClasses>
            <param>com.example.*</param>  <!-- adjust to your base package -->
        </targetClasses>
        <targetTests>
            <param>com.example.*</param>
        </targetTests>
        <excludedTestClasses>
            <param>*IT</param>
            <param>*IntegrationTest</param>
            <param>*E2ETest</param>
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
        <withHistory>true</withHistory>
        <historyInputFile>${project.build.directory}/pitest-history.bin</historyInputFile>
        <historyOutputFile>${project.build.directory}/pitest-history.bin</historyOutputFile>
        <mutators>DEFAULTS</mutators>
        <timestampedReports>false</timestampedReports>
    </configuration>
</plugin>
```

Run:
```bash
mvn test-compile pitest:mutationCoverage
```

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

If you get `InaccessibleObjectException` or module-related failures, add JVM args:

```xml
<!-- Maven: in pitest plugin config -->
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
