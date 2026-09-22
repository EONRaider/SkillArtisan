/** Skill validation logic. */
import * as path from "node:path";
import { ParseError } from "./errors.js";
import { findSkillMd, parseFrontmatter } from "./parser.js";
import { promises as fs } from "node:fs";
const MAX_SKILL_NAME_LENGTH = 64;
const MAX_DESCRIPTION_LENGTH = 1024;
const MAX_COMPATIBILITY_LENGTH = 500;
/** Check if a character is a Unicode letter. */
function isLetter(c) {
    // Check using Unicode character categories - simpler approach
    const code = c.codePointAt(0);
    if (code === undefined)
        return false;
    // Basic Latin
    if ((code >= 65 && code <= 90) || (code >= 97 && code <= 122))
        return true;
    // Digits 0-9
    if (code >= 48 && code <= 57)
        return true;
    // Cyrillic
    if (code >= 0x0400 && code <= 0x04ff)
        return true;
    // CJK Unified Ideographs
    if (code >= 0x4e00 && code <= 0x9fff)
        return true;
    // CJK Extension A
    if (code >= 0x3400 && code <= 0x4dbf)
        return true;
    // Combining diacritical marks
    if (code >= 0x0300 && code <= 0x036f)
        return true;
    // Latin Extended
    if (code >= 0x00c0 && code <= 0x024f)
        return true;
    return false;
}
/** Check if a character is a digit. */
function isDigit(c) {
    const code = c.codePointAt(0);
    return code !== undefined && code >= 48 && code <= 57; // 0-9
}
// Allowed frontmatter fields per Agent Skills Spec
const ALLOWED_FIELDS = new Set([
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
]);
/** Normalize a string using NFKC normalization. */
function normalize(text) {
    return text.normalize("NFKC");
}
/** Validate skill name format and directory match.
 *
 * Skill names support i18n characters (Unicode letters) plus hyphens.
 * Names must be lowercase and cannot start/end with hyphens.
 */
function validateName(name, skillDir) {
    const errors = [];
    if (!name || typeof name !== "string" || !name.trim()) {
        errors.push("Field 'name' must be a non-empty string");
        return errors;
    }
    const normalized = normalize(name.trim());
    if (normalized.length > MAX_SKILL_NAME_LENGTH) {
        errors.push(`Skill name '${normalized}' exceeds ${MAX_SKILL_NAME_LENGTH} character limit (${normalized.length} chars)`);
    }
    if (normalized !== normalized.toLowerCase()) {
        errors.push(`Skill name '${normalized}' must be lowercase`);
    }
    if (normalized.startsWith("-") || normalized.endsWith("-")) {
        errors.push("Skill name cannot start or end with a hyphen");
    }
    if (normalized.includes("--")) {
        errors.push("Skill name cannot contain consecutive hyphens");
    }
    // Allow Unicode letters (including i18n characters), digits, and hyphens
    // We check if name contains only letters, numbers, and hyphens
    const hasInvalidChars = Array.from(normalized).some((c) => !(isLetter(c) || isDigit(c) || c === "-"));
    if (hasInvalidChars) {
        errors.push(`Skill name '${normalized}' contains invalid characters. Only letters, digits, and hyphens are allowed.`);
    }
    if (skillDir) {
        const dirName = normalize(path.basename(skillDir));
        if (dirName !== normalized) {
            errors.push(`Directory name '${path.basename(skillDir)}' must match skill name '${normalized}'`);
        }
    }
    return errors;
}
/** Validate description format. */
function validateDescription(description) {
    const errors = [];
    if (!description || typeof description !== "string" || !description.trim()) {
        errors.push("Field 'description' must be a non-empty string");
        return errors;
    }
    if (description.length > MAX_DESCRIPTION_LENGTH) {
        errors.push(`Description exceeds ${MAX_DESCRIPTION_LENGTH} character limit (${description.length} chars)`);
    }
    return errors;
}
/** Validate compatibility format. */
function validateCompatibility(compatibility) {
    const errors = [];
    if (typeof compatibility !== "string") {
        errors.push("Field 'compatibility' must be a string");
        return errors;
    }
    if (compatibility.length > MAX_COMPATIBILITY_LENGTH) {
        errors.push(`Compatibility exceeds ${MAX_COMPATIBILITY_LENGTH} character limit (${compatibility.length} chars)`);
    }
    return errors;
}
/** Validate that only allowed fields are present. */
function validateMetadataFields(metadata) {
    const errors = [];
    const extraFields = Object.keys(metadata).filter((k) => !ALLOWED_FIELDS.has(k));
    if (extraFields.length > 0) {
        errors.push(`Unexpected fields in frontmatter: ${extraFields.sort().join(", ")}. Only ${[...ALLOWED_FIELDS].sort().join(", ")} are allowed.`);
    }
    return errors;
}
/** Validate parsed skill metadata.
 *
 * This is the core validation function that works on already-parsed metadata,
 * avoiding duplicate file I/O when called from the parser.
 *
 * @param metadata - Parsed YAML frontmatter dictionary
 * @param skillDir - Optional path to skill directory (for name-directory match check)
 * @returns List of validation error messages. Empty list means valid.
 */
export function validateMetadata(metadata, skillDir) {
    const errors = [];
    errors.push(...validateMetadataFields(metadata));
    if (!("name" in metadata)) {
        errors.push("Missing required field in frontmatter: name");
    }
    else {
        errors.push(...validateName(String(metadata.name), skillDir ?? ""));
    }
    if (!("description" in metadata)) {
        errors.push("Missing required field in frontmatter: description");
    }
    else {
        errors.push(...validateDescription(String(metadata.description)));
    }
    if ("compatibility" in metadata) {
        errors.push(...validateCompatibility(metadata.compatibility));
    }
    return errors;
}
/** Validate a skill directory.
 *
 * @param skillDir - Path to the skill directory
 * @returns List of validation error messages. Empty list means valid.
 */
export async function validate(skillDir) {
    const resolvedDir = path.resolve(skillDir);
    try {
        await fs.access(resolvedDir);
    }
    catch {
        return [`Path does not exist: ${resolvedDir}`];
    }
    try {
        const stat = await fs.stat(resolvedDir);
        if (!stat.isDirectory()) {
            return [`Not a directory: ${resolvedDir}`];
        }
    }
    catch {
        return [`Not a directory: ${resolvedDir}`];
    }
    const skillMd = await findSkillMd(resolvedDir);
    if (skillMd === null) {
        return ["Missing required file: SKILL.md"];
    }
    try {
        const content = await fs.readFile(skillMd, "utf-8");
        const [metadata] = parseFrontmatter(content);
        return validateMetadata(metadata, resolvedDir);
    }
    catch (e) {
        if (e instanceof ParseError) {
            return [e.message];
        }
        return [String(e)];
    }
}
//# sourceMappingURL=validator.js.map