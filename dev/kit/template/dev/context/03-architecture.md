# 03 · Code Architecture

> How does it work. Module structure · data flow · dependencies · interfaces.
> Changes when: **the implementation approach changes.**
> ID rule: start at `U-01` (units/modules). Cross-reference as `↔ F-xxx ↔ D-xx`.

## Directories

```
<main directories and the responsibility of each>
```

## Dependency Direction

```
<allowed dependency directions between layers; rules forbidding reverse dependencies>
```

<!-- Template

## U-01 · <module name>

**Responsibility**: <one line. If it needs two, it's time to split>
**Public interface**:
```ts
<signature>
```
**Depends on**: U-xx, <external packages>
**Data flow**: <from input to output>

**References**: F-xxx, D-xx

-->
