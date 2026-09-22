/** YAML frontmatter parsing for SKILL.md files. */
import * as yaml from "js-yaml";
import { promises as fs } from "node:fs";
import * as path from "node:path";
import { ParseError, ValidationError } from "./errors.js";
import { SkillProperties } from "./models.js";
/** Find the SKILL.md file in a skill directory.
 *
 * Prefers SKILL.md (uppercase) but accepts skill.md (lowercase).
 *
 * @param skillDir - Path to the skill directory
 * @returns Path to the SKILL.md file, or null if not found
 */
export async function findSkillMd(skillDir) {
    for (const name of ["SKILL.md", "skill.md"]) {
        const filePath = path.join(skillDir, name);
        try {
            await fs.access(filePath);
            return filePath;
        }
        catch {
            // File doesn't exist, continue
        }
    }
    return null;
}
/** Parse YAML frontmatter from SKILL.md content.
 *
 * @param content - Raw content of SKILL.md file
 * @returns Tuple of (metadata dict, markdown body)
 * @throws ParseError If frontmatter is missing or invalid
 */
export function parseFrontmatter(content) {
    if (!content.startsWith("---")) {
        throw new ParseError("SKILL.md must start with YAML frontmatter (---)");
    }
    const parts = content.split("---", 3);
    if (parts.length < 3) {
        throw new ParseError("SKILL.md frontmatter not properly closed with ---");
    }
    const frontmatterStr = parts[1];
    const body = parts[2].trim();
    let metadata;
    try {
        const parsed = yaml.load(frontmatterStr);
        // Check if parsed value is an array (list in YAML terms)
        if (Array.isArray(parsed)) {
            throw new ParseError("SKILL.md frontmatter must be a YAML mapping");
        }
        metadata = (parsed ?? {});
    }
    catch (e) {
        throw new ParseError(`Invalid YAML in frontmatter: ${e}`);
    }
    if (typeof metadata !== "object" || metadata === null) {
        throw new ParseError("SKILL.md frontmatter must be a YAML mapping");
    }
    if ("metadata" in metadata) {
        const metaValue = metadata.metadata;
        if (typeof metaValue === "object" && metaValue !== null) {
            metadata.metadata = Object.fromEntries(Object.entries(metaValue).map(([k, v]) => [String(k), String(v)]));
        }
    }
    return [metadata, body];
}
/** Read skill properties from SKILL.md frontmatter.
 *
 * This function parses the frontmatter and returns properties.
 * It does NOT perform full validation. Use validate() for that.
 *
 * @param skillDir - Path to the skill directory
 * @returns SkillProperties with parsed metadata
 * @throws ParseError If SKILL.md is missing or has invalid YAML
 * @throws ValidationError If required fields (name, description) are missing
 */
export async function readProperties(skillDir) {
    const skillMd = await findSkillMd(skillDir);
    if (skillMd === null) {
        throw new ParseError(`SKILL.md not found in ${skillDir}`);
    }
    const content = await fs.readFile(skillMd, "utf-8");
    const [metadata] = parseFrontmatter(content);
    if (!("name" in metadata)) {
        throw new ValidationError("Missing required field in frontmatter: name");
    }
    if (!("description" in metadata)) {
        throw new ValidationError("Missing required field in frontmatter: description");
    }
    const name = metadata.name;
    const description = metadata.description;
    if (typeof name !== "string" || !name.trim()) {
        throw new ValidationError("Field 'name' must be a non-empty string");
    }
    if (typeof description !== "string" || !description.trim()) {
        throw new ValidationError("Field 'description' must be a non-empty string");
    }
    return new SkillProperties(name.trim(), description.trim(), metadata.license, metadata.compatibility, metadata["allowed-tools"], metadata.metadata ?? {});
}
//# sourceMappingURL=parser.js.map