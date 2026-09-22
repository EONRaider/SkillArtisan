/** Skill-related exceptions. */
/** Base exception for all skill-related errors. */
export class SkillError extends Error {
    constructor(message) {
        super(message);
        this.name = "SkillError";
    }
}
/** Raised when SKILL.md parsing fails. */
export class ParseError extends SkillError {
    constructor(message) {
        super(message);
        this.name = "ParseError";
    }
}
/** Raised when skill properties are invalid. */
export class ValidationError extends SkillError {
    /** List of validation error messages (may contain just one) */
    errors;
    constructor(message, errors) {
        super(message);
        this.name = "ValidationError";
        this.errors = errors ?? [message];
    }
}
//# sourceMappingURL=errors.js.map