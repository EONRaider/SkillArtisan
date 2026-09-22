/** Skill-related exceptions. */
/** Base exception for all skill-related errors. */
export declare class SkillError extends Error {
    constructor(message: string);
}
/** Raised when SKILL.md parsing fails. */
export declare class ParseError extends SkillError {
    constructor(message: string);
}
/** Raised when skill properties are invalid. */
export declare class ValidationError extends SkillError {
    /** List of validation error messages (may contain just one) */
    readonly errors: string[];
    constructor(message: string, errors?: string[]);
}
//# sourceMappingURL=errors.d.ts.map