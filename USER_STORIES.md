# Catalog of User Stories: Campus Lost & Found App

This document provides a numbered catalog of user stories covering all functional requirements specified in `FRs.md`. Each requirement is analyzed across three lenses:
1. **Standard Usage (Happy Path)**
2. **Edge Cases & Validation**
3. **Permission Boundaries & Security**

---

## FR-1: User Management
> *The system shall allow students and admins to register and log in using their name, email address, and phone number.*

### Standard Usage
- **US-1.1 (Student Registration):** As a student, I want to register an account using my full name, email address, and phone number, so that I can create and manage lost/found posts under my verified identity.
- **US-1.2 (Admin Registration):** As a campus administrator, I want to register an administrative account with an admin designation (or invitation/admin key), so that I can review pending posts and maintain platform safety.
- **US-1.3 (User Login):** As a registered student or admin, I want to log in using my registered email address and credentials, so that I can establish an authenticated session.
- **US-1.4 (Current User Identity):** As an authenticated user, I want to retrieve my current session profile (name, email, phone number, and role), so that the application can display my identity and load authorized UI controls.
- **US-1.5 (User Logout):** As an authenticated user, I want to log out of my session, so that subsequent users on a shared computer cannot access my account.

### Edge Cases & Validation
- **US-1.6 (Duplicate Email Rejection):** As a system, I want to reject registration requests containing an email address that is already registered (returning HTTP 409 Conflict), so that user accounts remain unique.
- **US-1.7 (Required Field Validation):** As a system, I want to reject registration submissions missing `name`, `email`, or `phone_number` with an HTTP 422 Unprocessable Entity, so that incomplete records are not created.
- **US-1.8 (Email Format Validation):** As a system, I want to validate that the provided email follows standard email syntax (e.g. `user@campus.edu`), rejecting malformed emails with HTTP 422.
- **US-1.9 (Phone Number Formatting):** As a system, I want to validate that the provided phone number contains valid digit characters (e.g. 10 to 15 digits), preventing arbitrary text strings.
- **US-1.10 (Invalid Login Credentials):** As a system, I want to reject login attempts with unregistered emails or incorrect credentials with HTTP 401 Unauthorized, without revealing whether the email exists.

### Permission Boundaries
- **US-1.11 (Anonymous Access Limits):** As a system, I want to deny unauthenticated access to protected user management endpoints (such as `GET /users/me`), returning HTTP 401 Unauthorized.
- **US-1.12 (Privilege Escalation Prevention):** As a system, I want to prevent standard users from escalating their role to `admin` through public registration or profile modification payloads, enforcing strict server-side role assignment.

---

## FR-2: Item Posting
> *The system shall allow students to create, edit, and mark posts as resolved, capturing the title, description, item type (lost or found), and campus location.*

### Standard Usage
- **US-2.1 (Create Lost Item Post):** As a student who lost a personal belonging, I want to create a post specifying a title, detailed description, item type (`lost`), and campus location (e.g., "Library 2nd Floor"), so that fellow students can help me locate it.
- **US-2.2 (Create Found Item Post):** As a student who found an unattended item, I want to create a post specifying item type (`found`), title, description, and campus location, so that the rightful owner can identify and claim it.
- **US-2.3 (Edit Own Item Post):** As a student post author, I want to update the title, description, or campus location of my post, so that I can correct errors or provide updated details.
- **US-2.4 (Mark Item as Resolved):** As a student post author, I want to mark my active post as resolved once the item is recovered or returned, so that the community knows the case is closed.
- **US-2.5 (View Single Item Details):** As a campus student or visitor, I want to view the full details of an item post (title, description, item type, campus location, resolution status, creation date, and poster contact name), so that I can assess whether it matches what I lost or found.

### Edge Cases & Validation
- **US-2.6 (Item Type Enumeration):** As a system, I want to validate that `item_type` strictly matches either `lost` or `found`, rejecting invalid strings (e.g., `stolen`, `misc`) with HTTP 422.
- **US-2.7 (Mandatory Field Enforcement):** As a system, I want to reject item creation or updates that have an empty title, blank description, or missing campus location with HTTP 422.
- **US-2.8 (Field Length Constraints):** As a system, I want to enforce reasonable character boundaries (e.g. title: 3–100 characters; description: 10–2000 characters; location: 2–100 characters) to prevent database truncation or spam payloads.
- **US-2.9 (Non-Existent Post Operations):** As a system, I want to return HTTP 404 Not Found whenever an operation targets an item ID that does not exist in the database.
- **US-2.10 (Idempotent Resolution):** As a system, I want to gracefully handle requests to mark an already-resolved post as resolved without causing data corruption or error.

### Permission Boundaries
- **US-2.11 (Authenticated Posting Only):** As a system, I want to reject post creation attempts by unauthenticated users with HTTP 401 Unauthorized, ensuring all posts are linked to a registered student.
- **US-2.12 (Author Ownership Guard on Updates):** As a system, I want to reject edit requests from users who are not the original author of the post (or an admin) with HTTP 403 Forbidden.
- **US-2.13 (Author Ownership Guard on Resolution):** As a system, I want to ensure only the post author or an administrator can mark an item post as resolved, returning HTTP 403 Forbidden to any unauthorized user.

---

## FR-3: Photo Attachments
> *The system shall allow students to upload one or more photos with captions and associate them with a specific item post.*

### Standard Usage
- **US-3.1 (Attach Single Photo with Caption):** As a student post author, I want to upload an image of the item along with an explanatory caption (e.g., "Front view showing sticker"), so that viewers can visually identify the item.
- **US-3.2 (Attach Multiple Photos):** As a student post author, I want to upload multiple photos (each with its own caption) to the same post, so that I can show different angles, serial numbers, or condition marks.
- **US-3.3 (Display Photos on Item View):** As a user viewing an item post, I want to see all associated photos in a clean gallery with their captions, so that I can inspect the visual evidence.

### Edge Cases & Validation
- **US-3.4 (File Type Validation):** As a system, I want to validate image file types (allowing only JPEG, PNG, and WebP), rejecting executables, scripts, or non-image documents (e.g., `.pdf`, `.exe`) with HTTP 400 or 422.
- **US-3.5 (File Size Limit Enforcement):** As a system, I want to reject image uploads that exceed the allowed file size limit (e.g. 5 MB) or 0-byte empty files with HTTP 400 Bad Request, protecting storage and network resources.
- **US-3.6 (Caption Length Boundary):** As a system, I want to validate that photo captions do not exceed 255 characters, rejecting excessively long strings with HTTP 422.
- **US-3.7 (Upload to Non-Existent Post):** As a system, I want to return HTTP 404 Not Found if a photo upload request specifies an `item_id` that does not exist.

### Permission Boundaries
- **US-3.8 (Photo Attachment Ownership Guard):** As a system, I want to prevent students from uploading photos to posts created by another student, returning HTTP 403 Forbidden.
- **US-3.9 (Unauthenticated Photo Upload Block):** As a system, I want to reject photo uploads from unauthenticated users with HTTP 401 Unauthorized.

---

## FR-4: Moderation Records
> *The system shall require an admin to review pending item posts and log an approval record containing the decision (approve/reject), review comments, and review timestamp.*

### Standard Usage
- **US-4.1 (Admin Pending Queue):** As an administrator, I want to access a dedicated queue of all item posts currently in `pending` status, so that I can inspect newly created items before they are displayed publicly.
- **US-4.2 (Approve Item Post):** As an administrator, I want to approve a compliant post, recording my decision (`approved`), review comments (e.g., "Verified student post"), and the review timestamp, so that the post becomes publicly searchable and visible.
- **US-4.3 (Reject Item Post):** As an administrator, I want to reject a non-compliant or inappropriate post, logging my decision (`rejected`), mandatory explanatory review comments, and the review timestamp, so that the author understands why the post was not published.
- **US-4.4 (Audit Trail Inspection):** As an administrator, I want to view the full moderation log for an item (decision, reviewer name/ID, comments, and review timestamp), so that moderation actions remain transparent and accountable.
- **US-4.5 (Author Status Notification):** As a student post author, I want to view the moderation status and review comments of my own posts, so that I know whether my post is approved or why it was rejected.

### Edge Cases & Validation
- **US-4.6 (Mandatory Rejection Comment):** As a system, I want to enforce that review comments cannot be empty when an item is rejected, returning HTTP 422 if an admin attempts to reject without providing a reason.
- **US-4.7 (Decision Enum Validation):** As a system, I want to restrict moderation decisions strictly to `approved` or `rejected`, rejecting any other values with HTTP 422.
- **US-4.8 (Immutable Timestamping):** As a system, I want to automatically set the `reviewed_at` timestamp on the server at the moment of the moderation decision, preventing client-side clock tampering.
- **US-4.9 (Review of Already Moderated Items):** As a system, I want to allow re-reviewing or auditing an item while appending or updating moderation records without corrupting existing database relationships.

### Permission Boundaries
- **US-4.10 (Admin Role Protection):** As a system, I want to restrict access to moderation endpoints (`/moderation/pending`, `/moderation/{item_id}/review`) strictly to users with the `admin` role, returning HTTP 403 Forbidden to regular students and HTTP 401 to anonymous users.
- **US-4.11 (Public Feed Isolation):** As a system, I want to ensure that posts with `pending` or `rejected` status are never visible on the public feed or general search, remaining visible only to their creator and system admins.

---

## FR-5: Search and Filtering
> *The system shall provide a dedicated search feature that allows users to search posts by keyword and filter by item type and campus location.*

### Standard Usage
- **US-5.1 (Keyword Search):** As a student searching for a lost item, I want to search posts using keywords (e.g., "AirPods", "black hydroflask"), matching against post titles and descriptions, so that I can quickly locate relevant items.
- **US-5.2 (Filter by Item Type):** As a user, I want to filter listings by item type (`lost` or `found`), so that I only see items that match my current context.
- **US-5.3 (Filter by Campus Location):** As a user, I want to filter posts by specific campus locations (e.g., "Library", "Student Union", "Gym"), so that I can focus on where I lost or found an object.
- **US-5.4 (Combined Search and Filtering):** As a user, I want to apply keyword search, item type filter, and campus location filter simultaneously, so that I can narrow down large numbers of posts efficiently.
- **US-5.5 (Resolution Status Filter):** As a user, I want to toggle between active (unresolved) items and resolved items, defaulting to active items, so that search results are not cluttered by closed cases.

### Edge Cases & Validation
- **US-5.6 (Empty Query Behavior):** As a user submitting an empty keyword string or blank filters, I want the system to return all approved, active items in descending chronological order without throwing errors.
- **US-5.7 (No Matching Results):** As a user whose search criteria yield no matching posts, I want the system to return an HTTP 200 with an empty list (`[]`) and display a clear, helpful "No items found" message in the UI.
- **US-5.8 (Special Character Handling):** As a system, I want to safely sanitize search terms containing punctuation, wildcard characters (`%`, `_`), and quotes, preventing SQL syntax errors or SQL injection vulnerabilities.
- **US-5.9 (Case-Insensitive Search):** As a user, I want search matching to be case-insensitive (e.g., searching for "keys", "Keys", or "KEYS" yields the same results), ensuring high findability.

### Permission Boundaries
- **US-5.10 (Public Search Availability):** As an unregistered campus guest, I want to search and filter approved posts without having to register or log in first, lowering the barrier to finding lost items.
- **US-5.11 (Moderation Boundary in Search):** As a system, I want to strictly exclude any `pending` or `rejected` items from search results returned to public users, ensuring that only admin-approved posts are discoverable.
