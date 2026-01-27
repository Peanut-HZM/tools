# Community Knowledge Research: wordpress-plugin-core

**Research Date**: 2026-01-21
**Packages Researched**: WordPress 6.7+, 6.8, 6.9 (released 2024-2025)
**Time Window**: May 2024 - January 2026 (post-cutoff focus)
**Official Repo**: WordPress/WordPress

---

## Summary

- **Total Findings**: 15
- **TIER 1**: 8 findings (Official WordPress sources)
- **TIER 2**: 5 findings (High-quality community)
- **TIER 3**: 2 findings (Community consensus)
- **TIER 4**: 0 findings (flagged for verification)

**Key Discovery Areas**:
- WordPress 6.8 bcrypt password hashing (major security change)
- WordPress 6.9 WP_Dependencies deprecation (breaking change)
- REST API security vulnerabilities (2025-2026)
- Translation loading changes in 6.7
- Plugin compatibility issues across 6.7-6.9

---

## TIER 1 Findings (Official Sources)

### Finding 1.1: WordPress 6.8 bcrypt Password Hashing Migration

**Source**: [WordPress Core Make](https://make.wordpress.org/core/2025/02/17/wordpress-6-8-will-use-bcrypt-for-password-hashing/)
**Issue**: WordPress 6.8 switches from phpass to bcrypt password hashing
**Impact**: High (affects all password handling)
**Applies to**: WordPress 6.8+ (released April 2025)

**What Changed**:
- Default password hashing algorithm changed from phpass to bcrypt
- New hash prefix: `$wp$2y$` (SHA-384 pre-hashed bcrypt)
- Existing passwords automatically rehashed on next login
- Popular bcrypt plugins (roots/wp-password-bcrypt) now redundant

**Plugin Compatibility**:
```php
// ✅ SAFE - These functions continue to work without changes
wp_hash_password( $password );
wp_check_password( $password, $hash );

// ⚠️ NEEDS UPDATE - Direct phpass hash handling
if ( strpos( $hash, '$P$' ) === 0 ) {
    // Custom phpass logic - needs update for bcrypt
}

// ✅ NEW - Detect hash type
if ( strpos( $hash, '$wp$2y$' ) === 0 ) {
    // bcrypt hash
}
```

**Action Required**:
- Review plugins that directly handle password hashes
- Remove bcrypt plugins when upgrading to 6.8+
- No action needed for standard wp_hash_password/wp_check_password usage

**References**:
- [GitHub Issue #21022](https://core.trac.wordpress.org/ticket/21022)
- [Roots bcrypt package](https://github.com/roots/wp-password-bcrypt)

---

### Finding 1.2: WordPress 6.9 WP_Dependencies Deprecation

**Source**: [WordPress Support Forum](https://wordpress.org/support/topic/after-automatic-updating-to-6-9-deprecated-function-wp_dependencies/)
**Issue**: WP_Dependencies object deprecated in WordPress 6.9
**Impact**: High (affects plugin asset management)
**Applies to**: WordPress 6.9+ (released December 2, 2025)

**Error Messages**:
```
Deprecated: Function WP_Dependencies->add_data() was called with an argument
that is deprecated since version 6.9.0!
```

**Why It Breaks**:
WordPress 6.9 removed or modified several deprecated functions that older themes and plugins relied on, breaking custom menu walkers, classic widgets, media modals, and customizer features.

**Affected Plugins** (confirmed):
- WooCommerce (fixed in 10.4.2)
- Yoast SEO (fixed in 26.6)
- Elementor (requires 3.24+)

**Unmaintained Plugins**:
While top 1,000 plugins patched within hours, the remaining 60,000+ plugins often lag behind. If 40% of plugins are at risk, it's because they fall into the "unmaintained" category with deprecated function usage.

**Action Required**:
- Test plugins with WP_DEBUG enabled on WordPress 6.9
- Replace deprecated WP_Dependencies methods
- Check for deprecation notices in debug.log

**References**:
- [WordPress 6.9 Breaking Changes](https://www.365i.co.uk/blog/2025/12/02/wordpress-6-9-broke-3-plugins-fix/)
- [WordPress 6.9 Overview](https://wordpress.org/documentation/wordpress-version/version-6-9/)

---

### Finding 1.3: Translation Loading Changes in WordPress 6.7

**Source**: [WooCommerce Developer Blog](https://developer.woocommerce.com/2024/11/11/developer-advisory-translation-loading-changes-in-wordpress-6-7/)
**Issue**: WordPress 6.7 changed when/how translations load
**Impact**: Medium (affects i18n functionality)
**Applies to**: WordPress 6.7+ (released November 12, 2024)

**What Changed**:
WordPress 6.7 is changing how translations are loaded, aiming to improve i18n best practices. Plugins loading translations too early may encounter issues.

**Common Issue**:
```php
// ❌ WRONG - Loading too early
add_action( 'init', 'load_plugin_textdomain' );

// ✅ CORRECT - Load after 'init' priority 10
add_action( 'init', 'load_plugin_textdomain', 11 );
```

**WooCommerce Fix**:
WooCommerce 9.4+ addresses early translation loading, though some users may still encounter debug notices under certain configurations.

**Action Required**:
- Review when load_plugin_textdomain() is called
- Ensure text domain matches plugin slug exactly
- Test with WP_DEBUG enabled

**References**:
- [WordPress 6.7 Field Guide](https://make.wordpress.org/core/2024/10/23/wordpress-6-7-field-guide/)

---

### Finding 1.4: Plugin Template Registration API Naming Changes

**Source**: [WordPress 6.7 Field Guide](https://make.wordpress.org/core/2024/10/23/wordpress-6-7-field-guide/)
**Issue**: Function names changed when API moved from Gutenberg to core
**Impact**: Low (only affects early adopters)
**Applies to**: WordPress 6.7+

**What Changed**:
When the Plugin Template Registration API was initially introduced, functions had a `wp_` prefix, but it was removed in Gutenberg 19.5 and WordPress 6.7 to adhere to naming conventions.

**Action Required**:
- If you experimented with this API before 6.7, check function names
- Update any references to old `wp_` prefixed functions

---

### Finding 1.5: New Block Metadata Collection Function

**Source**: [WordPress 6.7 Field Guide](https://make.wordpress.org/core/2024/10/23/wordpress-6-7-field-guide/)
**Issue**: New efficiency function for plugins with many blocks
**Impact**: Low (performance optimization)
**Applies to**: WordPress 6.7+

**New Feature**:
```php
// New in WordPress 6.7
wp_register_block_metadata_collection();
```

**Purpose**:
Helps plugins load block types more efficiently. Useful for plugins that include many blocks.

**Action Required**:
- Consider implementing for plugins with 5+ blocks
- Review performance improvements in testing

---

### Finding 1.6: show_in_rest Required for Gutenberg Block Editor

**Source**: [WordPress VIP Documentation](https://docs.wpvip.com/wordpress-on-vip/block-editor/)
**Issue**: Custom post types require REST API to use block editor
**Impact**: High (affects CPT registration)
**Applies to**: WordPress 5.0+ (still commonly missed in 2025)

**Critical Rule**:
Only post types registered with `'show_in_rest' => true` are compatible with the block editor. The block editor is dependent on the WordPress REST API.

**Common Mistake**:
```php
// ❌ WRONG - Block editor won't work
register_post_type( 'book', array(
    'public' => true,
    'supports' => array('editor'),
    // Missing show_in_rest!
) );

// ✅ CORRECT
register_post_type( 'book', array(
    'public' => true,
    'show_in_rest' => true,  // Required for block editor
    'supports' => array('editor'),
) );
```

**Fallback**:
For post types that are incompatible with the block editor—or have `show_in_rest => false`—the classic editor will load instead.

**Action Required**:
- Add to SKILL.md under Custom Post Types section
- Include in common errors checklist

**References**:
- [GitHub Issue #7595](https://github.com/WordPress/gutenberg/issues/7595)

---

### Finding 1.7: flush_rewrite_rules() Performance Warning

**Source**: [Permalink Manager Pro](https://permalinkmanager.pro/blog/flush-rewrite-rules/)
**Issue**: Calling flush_rewrite_rules() on every page load causes database overload
**Impact**: High (performance)
**Applies to**: All WordPress versions

**What NOT to Do**:
```php
// ❌ WRONG - Runs on EVERY page load
add_action( 'init', 'mypl_register_cpt' );
add_action( 'init', 'flush_rewrite_rules' );  // BAD!

// ❌ WRONG - In functions.php
function mypl_register_cpt() {
    register_post_type( 'book', ... );
    flush_rewrite_rules();  // BAD!
}
```

**Correct Patterns**:
```php
// ✅ GOOD - Only on activation
register_activation_hook( __FILE__, function() {
    mypl_register_cpt();
    flush_rewrite_rules();
} );

// ✅ GOOD - Only on deactivation
register_deactivation_hook( __FILE__, function() {
    flush_rewrite_rules();
} );

// ✅ GOOD - For theme activation
add_action( 'after_switch_theme', 'flush_rewrite_rules' );
```

**User-Facing Fix**:
Users can manually flush by going to Settings → Permalinks → Save Changes (even without changes).

**Action Required**:
- Strengthen warning in Issue #7 (Rewrite Rules Not Flushed)
- Add performance note to flush_rewrite_rules() usage

**References**:
- [WPExplorer: Fix CPT 404 Errors](https://www.wpexplorer.com/post-type-404-error/)

---

### Finding 1.8: Deactivation vs Uninstall Data Handling

**Source**: [WordPress Plugin Handbook](https://developer.wordpress.org/plugins/plugin-basics/activation-deactivation-hooks/)
**Issue**: Confusion about when to delete data
**Impact**: High (user trust, data loss)
**Applies to**: All WordPress versions

**Best Practice** (2025 confirmation):
> "A good practice to follow is to leave data and files when a plugin is deactivated, but remove any trace of the plugin when it is uninstalled/deleted."

**Key Distinctions**:

| Hook | Purpose | When to Use |
|------|---------|-------------|
| `register_activation_hook()` | Setup | Create tables, add options, schedule cron |
| `register_deactivation_hook()` | Temporary cleanup | Unschedule cron, delete transients ONLY |
| `uninstall.php` | Permanent deletion | Delete all options, tables, user data |

**Security Warning** (2025):
> "You should not keep inactive or deactivated WordPress plugins installed on your website. Inactive plugins may contain executable files and can be used by hackers to hide malware or a backdoor."

**Action Required**:
- Already well-documented in Issue #15
- Add security warning about inactive plugins

**References**:
- [Liquid Web: Plugin Best Practices](https://www.liquidweb.com/wordpress/plugin/best-practices/)

---

## TIER 2 Findings (High-Quality Community)

### Finding 2.1: REST API Missing permission_callback Vulnerabilities (2025-2026)

**Sources**:
- [Patchstack: SureTriggers Vulnerability](https://patchstack.com/articles/critical-suretriggers-plugin-vulnerability-exploited-within-4-hours/)
- [WordPress Security Ninja](https://wpsecurityninja.com/wordpress-vulnerabilities-database/)

**Issue**: Missing or improper permission_callback on REST endpoints
**Impact**: Critical (allows unauthorized access)
**Evidence**: Multiple 2025-2026 vulnerabilities

**Recent Examples**:

**1. All in One SEO (AIOSEO) - 3M+ installations**
- Missing permission check on REST API endpoint
- Allowed contributor-level users to view global AI access token
- Fixed in version 4.9.3

**2. AI Engine Plugin (CVE-2025-11749) - 100K+ sites**
- CVSS score: 9.8 (Critical)
- Failed to include `show_in_index => false` during REST route registration
- Endpoints publicly visible in /wp-json/ index
- Allowed unauthenticated attackers to retrieve bearer token → full admin privileges

**3. SureTriggers Plugin**
- Insufficient authorization checks in REST API
- Failed to validate ST-Authorization HTTP header properly
- Exploited within 4 hours of disclosure

**4. Worker for Elementor (CVE-2025-66144)**
- Broken access control in REST API
- Subscriber-level privileges could invoke restricted features
- No patch available as of report date

**Common Pattern**:
```php
// ❌ VULNERABLE - Missing permission_callback
register_rest_route( 'myplugin/v1', '/data', array(
    'methods'  => 'GET',
    'callback' => 'my_callback',
    // WordPress 5.5+ requires permission_callback!
) );

// ✅ SECURE
register_rest_route( 'myplugin/v1', '/data', array(
    'methods'             => 'GET',
    'callback'            => 'my_callback',
    'permission_callback' => function() {
        return current_user_can( 'edit_posts' );
    },
) );

// ✅ SECURE - Hide from REST index for sensitive endpoints
register_rest_route( 'myplugin/v1', '/admin', array(
    'methods'             => 'POST',
    'callback'            => 'my_admin_callback',
    'permission_callback' => function() {
        return current_user_can( 'manage_options' );
    },
    'show_in_index'       => false,  // Don't expose in /wp-json/
) );
```

**2025-2026 Statistics**:
- 64,782 total vulnerabilities tracked in WordPress ecosystem
- 333 new vulnerabilities in one recent week
- 236 remained unpatched
- REST API auth issues represent significant percentage

**Action Required**:
- Expand Issue #13 with CVE examples
- Add `show_in_index => false` pattern
- Add to security checklist

**References**:
- [Search Engine Journal: AIOSEO Vulnerability](https://www.searchenginejournal.com/all-in-one-seo-wordpress-vulnerability-affects-over-3-million-sites/565104/)
- [SolidWP: Vulnerability Report Jan 2026](https://solidwp.com/blog/wordpress-vulnerability-report-january-7-2026/)

---

### Finding 2.2: wpdb::prepare() Table Name Escaping

**Source**: [WordPress Coding Standards Issue #2442](https://github.com/WordPress/WordPress-Coding-Standards/issues/2442)
**Issue**: Table names can't be used as placeholders in prepare()
**Impact**: Medium (common mistake)
**Applies to**: All WordPress versions

**The Problem**:
Using table names as placeholders adds quotes around the table name, breaking SQL syntax.

**Common Mistakes**:

```php
// ❌ WRONG - Adds quotes around table name
$table = $wpdb->prefix . 'my_table';
$wpdb->get_results( $wpdb->prepare(
    "SELECT * FROM %s WHERE id = %d",
    $table, $id
) );
// Result: SELECT * FROM 'wp_my_table' WHERE id = 1
// FAILS - table name is quoted

// ❌ WRONG - Hardcoded prefix
$wpdb->get_results( $wpdb->prepare(
    "SELECT * FROM wp_my_table WHERE id = %d",
    $id
) );
// FAILS if user changed table prefix

// ✅ CORRECT - Table name NOT in prepare()
$table = $wpdb->prefix . 'my_table';
$wpdb->get_results( $wpdb->prepare(
    "SELECT * FROM {$table} WHERE id = %d",
    $id
) );

// ✅ CORRECT - Using wpdb->prefix for built-in tables
$wpdb->get_results( $wpdb->prepare(
    "SELECT * FROM {$wpdb->posts} WHERE ID = %d",
    $id
) );
```

**Additional wpdb::prepare() Mistakes**:

1. **Missing Placeholders**:
```php
// ❌ WRONG
$wpdb->prepare( "SELECT * FROM {$wpdb->posts}" );
// Error: The query argument of wpdb::prepare() must have a placeholder

// ✅ CORRECT - Don't use prepare() if no dynamic data
$wpdb->get_results( "SELECT * FROM {$wpdb->posts}" );
```

2. **Percentage Sign Handling**:
```php
// ❌ WRONG
$wpdb->prepare( "SELECT * FROM {$wpdb->posts} WHERE post_title LIKE '%test%'" );

// ✅ CORRECT
$search = '%' . $wpdb->esc_like( $term ) . '%';
$wpdb->get_results( $wpdb->prepare(
    "SELECT * FROM {$wpdb->posts} WHERE post_title LIKE %s",
    $search
) );
```

3. **Mixing Argument Formats**:
```php
// ❌ WRONG - Can't mix individual args and array
$wpdb->prepare( "... WHERE id = %d AND name = %s", $id, array( $name ) );

// ✅ CORRECT - Pick one format
$wpdb->prepare( "... WHERE id = %d AND name = %s", $id, $name );
// OR
$wpdb->prepare( "... WHERE id = %d AND name = %s", array( $id, $name ) );
```

**Action Required**:
- Add to Issue #11 (Incorrect LIKE Queries)
- Create new "Common wpdb::prepare() Mistakes" section
- Add to troubleshooting guide

**References**:
- [SitePoint: Working with Databases](https://www.sitepoint.com/working-with-databases-in-wordpress/)
- [WisdmLabs: wpdb prepare IN clauses](https://wisdmlabs.com/blog/wpdb-prepare-in-clause-unknown-placeholders/)

---

### Finding 2.3: Nonce Verification Edge Cases

**Source**: [MalCare: wp_verify_nonce()](https://www.malcare.com/blog/wp_verify_nonce/)
**Issue**: Nonce behavior creates edge cases
**Impact**: Medium (affects form/AJAX security)
**Applies to**: All WordPress versions

**Edge Cases Identified**:

**1. Time-Based Return Values**:
```php
$result = wp_verify_nonce( $nonce, 'action' );
// Returns 1: Valid, generated 0-12 hours ago
// Returns 2: Valid, generated 12-24 hours ago
// Returns false: Invalid or expired

// ⚠️ EDGE CASE: Value 2 means "1 second to <24 hours old"
// Less precise than it appears
```

**2. Nonce Reusability**:
WordPress doesn't track if a nonce has been used. They can be used multiple times within the 12-24 hour window, contradicting "number used once" concept.

**3. Session Invalidation**:
A nonce is only valid when tied to a valid session. If a user logs out, all their nonces become invalid.

**Problem Scenario**:
```php
// User opens form (nonce generated)
// User logs out in another tab
// User submits form
// Nonce verification fails - confusing UX
```

**4. Caching Problems**:
Cache issues can cause mismatches when caching plugins or server-side caching serve an older nonce.

**Best Practice**:
> "Setting caching shorter than the nonce lifespan" - though this conflicts with cache efficiency.

**5. Not a Substitute for Authorization**:
```php
// ❌ INSUFFICIENT - Only checks origin, not permission
if ( wp_verify_nonce( $_POST['nonce'], 'delete_user' ) ) {
    delete_user( $_POST['user_id'] );
}

// ✅ CORRECT - Combine with capability check
if ( wp_verify_nonce( $_POST['nonce'], 'delete_user' ) &&
     current_user_can( 'delete_users' ) ) {
    delete_user( absint( $_POST['user_id'] ) );
}
```

**Key Principle** (2025 emphasis):
> "Nonces should never be relied on for authentication or authorization, access control. Protect your functions using current_user_can(). Always assume Nonces can be compromised."

**Action Required**:
- Expand Issue #3 (CSRF) with edge cases
- Add nonce limitations to security foundation
- Include caching warning

**References**:
- [Pressidium: Understanding WordPress Nonces](https://pressidium.com/blog/nonces-in-wordpress-all-you-need-to-know/)
- [WordPress Developer Blog: Understand and Use Nonces Properly](https://developer.wordpress.org/news/2023/08/understand-and-use-wordpress-nonces-properly/)

---

### Finding 2.4: Hook Priority and Multiple Arguments Gotchas

**Source**: [Kinsta: WordPress Hooks Bootcamp](https://kinsta.com/blog/wordpress-hooks/)
**Issue**: Hook priority and argument handling commonly misunderstood
**Impact**: Medium (affects hook functionality)
**Applies to**: All WordPress versions

**Key Gotchas**:

**1. Default Arguments**:
```php
// By default, callback receives only 1 argument
add_action( 'save_post', 'my_save_function' );
function my_save_function( $post_id ) {
    // $post_id is available
    // $post and $update are NOT available
}

// ✅ Specify argument count to receive more
add_action( 'save_post', 'my_save_function', 10, 3 );
function my_save_function( $post_id, $post, $update ) {
    // Now all 3 arguments are available
}
```

**2. Priority Matters**:
```php
// Lower number = runs earlier
add_action( 'init', 'first_function', 5 );   // Runs first
add_action( 'init', 'second_function', 10 );  // Default priority
add_action( 'init', 'third_function', 15 );   // Runs last
```

**3. Naming Collisions**:
> "Naming conflicts ('collisions') occur when two developers use the same hook name for completely different purposes, which leads to difficult to find bugs."

**Best Practice**:
```php
// ❌ GENERIC - Collision risk
do_action( 'data_processed' );

// ✅ PREFIXED - Unique to your plugin
do_action( 'mypl_data_processed', $data );
```

**4. Filter vs Action Confusion**:
```php
// ❌ WRONG - Echoing in filter
add_filter( 'the_content', function( $content ) {
    echo '<div>Extra content</div>';  // BAD!
    return $content;
} );

// ✅ CORRECT - Return modified data
add_filter( 'the_content', function( $content ) {
    return $content . '<div>Extra content</div>';
} );
```

**5. Backwards Compatibility**:
> "When a hook is added, there will be no way to remove it or make changes that will break backwards compatibility, so the hook should be in the right place when it is definitely needed and have the right name and parameters."

**Action Required**:
- Add "WordPress Hooks Gotchas" section
- Include in advanced topics
- Add to common errors reference

**References**:
- [Adam Brown: WP Hooks List](https://adambrown.info/p/wp_hooks/hook)

---

### Finding 2.5: Custom Post Type URL Conflicts

**Source**: [Permalink Manager Pro: URL Conflicts](https://permalinkmanager.pro/blog/wordpress-url-conflicts/)
**Issue**: Title/slug similarity causes 404 errors
**Impact**: Medium (affects CPT access)
**Applies to**: All WordPress versions

**The Problem**:
If you have a post type named 'portfolio' and also have a main 'Portfolio' page, both with the same slug, this creates a conflict that could cause 404 errors on your singular post type posts.

**Example Conflict**:
```php
// Register CPT with slug 'portfolio'
register_post_type( 'portfolio', array(
    'rewrite' => array( 'slug' => 'portfolio' ),
) );

// Also have a page:
// URL: example.com/portfolio/

// Individual portfolio posts 404:
// URL: example.com/portfolio/my-project/  ← CONFLICTS
```

**Solutions**:

```php
// 1. Use different slug for CPT
register_post_type( 'portfolio', array(
    'rewrite' => array( 'slug' => 'projects' ),
) );
// Posts: example.com/projects/my-project/
// Page: example.com/portfolio/

// 2. Use hierarchical slug
register_post_type( 'portfolio', array(
    'rewrite' => array( 'slug' => 'work/portfolio' ),
) );
// Posts: example.com/work/portfolio/my-project/

// 3. Rename the page slug
// Change page from /portfolio/ to /our-portfolio/
```

**Action Required**:
- Add to Issue #7 (Rewrite Rules Not Flushed)
- Include in CPT troubleshooting
- Add to common errors guide

**References**:
- [TechnoCrackers: Fixing Permalink Issues in CPTs](https://technocrackers.com/fixing-permalink-issues-in-custom-post-types/)

---

## TIER 3 Findings (Community Consensus)

### Finding 3.1: admin-ajax.php Performance vs REST API

**Source**: Multiple community sources (needs verification against official benchmarks)
**Issue**: admin-ajax.php is 10x slower than REST API
**Impact**: Medium (performance)
**Applies to**: All WordPress versions

**Current Skill Claims**:
> "REST API for new projects (10x faster)"

**Community Evidence**:
- [Delicious Brains comparison](https://deliciousbrains.com/comparing-wordpress-rest-api-performance-admin-ajax-php/) cited in SKILL.md
- Multiple 2025 sources recommend REST API over admin-ajax.php
- admin-ajax.php loads entire WordPress core

**Needs Verification**:
- Actual performance multiplier (10x may vary)
- Confirm official WordPress recommendation
- Test with WordPress 6.7+ performance improvements

**Action Required**:
- Verify claim with current benchmarks
- Update if performance ratio has changed
- Add caching considerations

---

### Finding 3.2: PHP 8.5 Compatibility

**Source**: [WordPress 6.9 Overview](https://wordpress.org/documentation/wordpress-version/version-6-9/)
**Issue**: WordPress 6.9 adds PHP 8.5 support
**Impact**: Low (future-proofing)
**Applies to**: WordPress 6.9+ and PHP 8.5 (when stable)

**Announcement**:
> "WordPress 6.9 is fully compatible with PHP 8.5, ensuring better performance, enhanced security and long-term support for upcoming WordPress versions."

**Recommendation**:
> "Plugin developers should test their code early to catch compatibility issues and deprecated functions to ensure plugins continue working smoothly when PHP 8.5 reaches stable adoption."

**Action Required**:
- Update "Latest Versions" section with PHP 8.5 mention
- Add to testing recommendations
- Monitor for PHP 8.5 specific deprecations

**References**:
- [Seahawk: WordPress 6.9 Overview](https://seahawkmedia.com/wordpress-news/wordpress-6-9-release-overview/)

---

## TIER 4 Findings (Low Confidence - DO NOT ADD)

None identified. All findings met TIER 3 or higher confidence.

---

## Recommended Actions

### Priority 1: High-Impact Additions (Implement Now)

1. **Add WordPress 6.8 bcrypt Section** (Finding 1.1)
   - Location: New section "WordPress Version-Specific Changes"
   - Content: Migration notes, compatibility code examples
   - Include removal notice for bcrypt plugins

2. **Expand REST API Security** (Finding 2.1)
   - Location: Issue #13
   - Add: CVE examples from 2025-2026
   - Add: `show_in_index => false` pattern
   - Add: Multiple real-world vulnerability examples

3. **Add show_in_rest Requirement** (Finding 1.6)
   - Location: Custom Post Types section
   - Make clear it's required for block editor
   - Add to common mistakes

4. **Strengthen flush_rewrite_rules() Warning** (Finding 1.7)
   - Location: Issue #7
   - Add performance impact warning
   - Show wrong patterns to avoid

### Priority 2: Edge Cases & Gotchas (Add Soon)

5. **Create "wpdb::prepare() Common Mistakes" Section** (Finding 2.2)
   - New section in Database patterns
   - Table name escaping
   - Percentage signs in LIKE queries
   - Missing placeholders error

6. **Expand Nonce Edge Cases** (Finding 2.3)
   - Location: Issue #3
   - Add caching problems
   - Add session invalidation
   - Add return value interpretation

7. **Add Hooks Gotchas** (Finding 2.4)
   - New section under "Advanced Topics"
   - Argument count defaults
   - Priority usage
   - Naming collisions

8. **Add CPT URL Conflicts** (Finding 2.5)
   - Location: Issue #7 or CPT section
   - Slug collision scenarios
   - Solutions with code examples

### Priority 3: Version Updates (Update Metadata)

9. **Update WordPress 6.9 Breaking Changes** (Finding 1.2)
   - Add to Known Issues or new section
   - WP_Dependencies deprecation
   - Plugin compatibility notes

10. **Add Translation Loading Changes** (Finding 1.3)
    - Location: Advanced Topics → i18n section
    - WordPress 6.7+ timing requirements

11. **Update Latest Versions Section**
    - WordPress 6.9 (December 2, 2025)
    - WordPress 7.0 expected (March/April 2026)
    - PHP 8.5 compatibility mention

### Priority 4: Verify & Update (Research Needed)

12. **Verify admin-ajax.php Performance Claims** (Finding 3.1)
    - Test REST API vs admin-ajax.php on WordPress 6.7+
    - Update performance multiplier if changed
    - Add modern benchmarks

---

## Not Recommended (Already Well Covered)

- **Deactivation vs Uninstall** (Finding 1.8) - Already documented in Issue #15
- **Plugin Dependencies** - Already documented in Issue #18
- **Block Metadata Collection** (Finding 1.5) - Low priority optimization
- **Plugin Template API** (Finding 1.4) - Affects too few developers

---

## Version-Specific Breaking Changes Summary

| WordPress Version | Released | Major Breaking Changes |
|-------------------|----------|------------------------|
| **6.7** "Rollins" | Nov 12, 2024 | Translation loading timing, Plugin Template API naming |
| **6.8** "Cecil" | Apr 15, 2025 | **bcrypt password hashing**, speculative loading |
| **6.9** "Gene" | Dec 2, 2025 | **WP_Dependencies deprecation**, Flash removal, PHP 8.5 support |
| **7.0** | Expected Mar/Apr 2026 | TBD |

---

## Sources

### Official WordPress Sources (TIER 1)
- [WordPress 6.7 Field Guide](https://make.wordpress.org/core/2024/10/23/wordpress-6-7-field-guide/)
- [WordPress 6.8 bcrypt Announcement](https://make.wordpress.org/core/2025/02/17/wordpress-6-8-will-use-bcrypt-for-password-hashing/)
- [WordPress 6.9 Documentation](https://wordpress.org/documentation/wordpress-version/version-6-9/)
- [WooCommerce Developer Advisory: Translation Changes](https://developer.woocommerce.com/2024/11/11/developer-advisory-translation-loading-changes-in-wordpress-6-7/)
- [WordPress Plugin Handbook: Activation/Deactivation Hooks](https://developer.wordpress.org/plugins/plugin-basics/activation-deactivation-hooks/)
- [WordPress VIP: Block Editor Documentation](https://docs.wpvip.com/wordpress-on-vip/block-editor/)
- [WordPress Core Trac: bcrypt Issue #21022](https://core.trac.wordpress.org/ticket/21022)

### High-Quality Community Sources (TIER 2)
- [Patchstack: SureTriggers Vulnerability](https://patchstack.com/articles/critical-suretriggers-plugin-vulnerability-exploited-within-4-hours/)
- [WordPress Security Ninja: Vulnerabilities Database](https://wpsecurityninja.com/wordpress-vulnerabilities-database/)
- [Search Engine Journal: AIOSEO Vulnerability](https://www.searchenginejournal.com/all-in-one-seo-wordpress-vulnerability-affects-over-3-million-sites/565104/)
- [SolidWP: Vulnerability Report January 2026](https://solidwp.com/blog/wordpress-vulnerability-report-january-7-2026/)
- [WordPress Coding Standards: wpdb::prepare() Issue](https://github.com/WordPress/WordPress-Coding-Standards/issues/2442)
- [MalCare: wp_verify_nonce Guide](https://www.malcare.com/blog/wp_verify_nonce/)
- [Kinsta: WordPress Hooks Bootcamp](https://kinsta.com/blog/wordpress-hooks/)
- [Permalink Manager Pro: Flush Rewrite Rules](https://permalinkmanager.pro/blog/flush-rewrite-rules/)
- [Permalink Manager Pro: URL Conflicts](https://permalinkmanager.pro/blog/wordpress-url-conflicts/)
- [GitHub: WordPress Gutenberg Issue #7595](https://github.com/WordPress/gutenberg/issues/7595)

### Community Consensus Sources (TIER 3)
- [365i: WordPress 6.9 Breaking Changes](https://www.365i.co.uk/blog/2025/12/02/wordpress-6-9-broke-3-plugins-fix/)
- [Seahawk: WordPress 6.9 Overview](https://seahawkmedia.com/wordpress-news/wordpress-6-9-release-overview/)
- [WPExplorer: Fix CPT 404 Errors](https://www.wpexplorer.com/post-type-404-error/)
- [SitePoint: Working with Databases](https://www.sitepoint.com/working-with-databases-in-wordpress/)

---

**Research Completed**: 2026-01-21
**Next Review**: After WordPress 7.0 release (Expected Mar/Apr 2026)
**Researcher**: Claude Code (Sonnet 4.5) - skill-researcher agent
