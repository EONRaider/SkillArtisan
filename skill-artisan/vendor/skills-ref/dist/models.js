/** Data models for Agent Skills. */
/** Properties parsed from a skill's SKILL.md frontmatter. */
export class SkillProperties {
    /** Skill name in kebab-case (required) */
    name;
    /** What the skill does and when the model should use it (required) */
    description;
    /** License for the skill (optional) */
    license;
    /** Compatibility information for the skill (optional) */
    compatibility;
    /** Tool patterns the skill requires (optional, experimental) */
    allowedTools;
    /** Key-value pairs for client-specific properties */
    metadata;
    constructor(name, description, license, compatibility, allowedTools, metadata = {}) {
        this.name = name;
        this.description = description;
        this.license = license;
        this.compatibility = compatibility;
        this.allowedTools = allowedTools;
        this.metadata = metadata;
    }
    /** Convert to dictionary, excluding undefined values. */
    toDict() {
        const result = {
            name: this.name,
            description: this.description,
        };
        if (this.license !== undefined) {
            result.license = this.license;
        }
        if (this.compatibility !== undefined) {
            result.compatibility = this.compatibility;
        }
        if (this.allowedTools !== undefined) {
            result["allowed-tools"] = this.allowedTools;
        }
        if (Object.keys(this.metadata).length > 0) {
            result.metadata = this.metadata;
        }
        return result;
    }
}
//# sourceMappingURL=models.js.map