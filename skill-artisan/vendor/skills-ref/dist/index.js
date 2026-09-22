/** Reference library for Agent Skills. */
export { SkillError, ParseError, ValidationError } from "./errors.js";
export { SkillProperties } from "./models.js";
export { findSkillMd, readProperties, parseFrontmatter } from "./parser.js";
export { toPrompt } from "./prompt.js";
export { validate, validateMetadata } from "./validator.js";
export const version = "0.1.5";
//# sourceMappingURL=index.js.map