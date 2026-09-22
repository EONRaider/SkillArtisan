/** YAML frontmatter parsing for SKILL.md files. */
import { SkillProperties } from "./models.js";
/** Find the SKILL.md file in a skill directory.
 *
 * Prefers SKILL.md (uppercase) but accepts skill.md (lowercase).
 *
 * @param skillDir - Path to the skill directory
 * @returns Path to the SKILL.md file, or null if not found
 */
export declare function findSkillMd(skillDir: string): Promise<string | null>;
/** Parse YAML frontmatter from SKILL.md content.
 *
 * @param content - Raw content of SKILL.md file
 * @returns Tuple of (metadata dict, markdown body)
 * @throws ParseError If frontmatter is missing or invalid
 */
export declare function parseFrontmatter(content: string): [Record<string, unknown>, string];
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
export declare function readProperties(skillDir: string): Promise<SkillProperties>;
//# sourceMappingURL=parser.d.ts.map