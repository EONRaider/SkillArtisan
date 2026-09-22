/** Data models for Agent Skills. */
/** Properties parsed from a skill's SKILL.md frontmatter. */
export declare class SkillProperties {
    /** Skill name in kebab-case (required) */
    readonly name: string;
    /** What the skill does and when the model should use it (required) */
    readonly description: string;
    /** License for the skill (optional) */
    readonly license?: string;
    /** Compatibility information for the skill (optional) */
    readonly compatibility?: string;
    /** Tool patterns the skill requires (optional, experimental) */
    readonly allowedTools?: string;
    /** Key-value pairs for client-specific properties */
    readonly metadata: Record<string, string>;
    constructor(name: string, description: string, license?: string, compatibility?: string, allowedTools?: string, metadata?: Record<string, string>);
    /** Convert to dictionary, excluding undefined values. */
    toDict(): Record<string, unknown>;
}
//# sourceMappingURL=models.d.ts.map