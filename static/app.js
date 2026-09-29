// Campus Lost & Found - Frontend Client Logic (Step 04: Admin Moderation System & Records)

const API_BASE = "";
let currentItems = [];
let currentUser = null;

// Helper: Escape HTML to avoid XSS
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Banner notification helper
function showBanner(message, type = "info") {
  const banner = document.getElementById("status-banner");
  const msgEl = document.getElementById("status-message");
  if (!banner || !msgEl) return;

  msgEl.textContent = message;
  banner.className = "p-4 rounded-lg text-sm mb-4 border transition-all flex items-center justify-between";

  if (type === "success") {
    banner.classList.add("bg-emerald-50", "border-emerald-200", "text-emerald-800");
  } else if (type === "error") {
    banner.classList.add("bg-rose-50", "border-rose-200", "text-rose-800");
  } else {
    banner.classList.add("bg-blue-50", "border-blue-200", "text-blue-800");
  }

  banner.classList.remove("hidden");
}

function dismissBanner() {
  const banner = document.getElementById("status-banner");
  if (banner) banner.classList.add("hidden");
}

// Switch between Login and Register tabs
function showAuthTab(tab) {
  dismissBanner();
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const tabLogin = document.getElementById("tab-login");
  const tabRegister = document.getElementById("tab-register");

  if (!loginForm || !registerForm) return;

  if (tab === "login") {
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
    if (tabLogin) tabLogin.className = "flex-1 py-3 text-sm font-semibold text-center border-b-2 border-indigo-600 text-indigo-600 transition";
    if (tabRegister) tabRegister.className = "flex-1 py-3 text-sm font-semibold text-center border-b-2 border-transparent text-slate-500 hover:text-slate-700 transition";
  } else {
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");
    if (tabLogin) tabLogin.className = "flex-1 py-3 text-sm font-semibold text-center border-b-2 border-transparent text-slate-500 hover:text-slate-700 transition";
    if (tabRegister) tabRegister.className = "flex-1 py-3 text-sm font-semibold text-center border-b-2 border-indigo-600 text-indigo-600 transition";
  }
}

// Update UI based on authentication state
function updateAuthUI(user = null) {
  currentUser = user;
  const navLoggedOut = document.getElementById("nav-logged-out");
  const navLoggedIn = document.getElementById("nav-logged-in");
  const navUserName = document.getElementById("nav-user-name");
  const navUserRole = document.getElementById("nav-user-role");
  const userToolbar = document.getElementById("user-toolbar");
  const toolbarName = document.getElementById("toolbar-name");
  const toolbarAvatar = document.getElementById("toolbar-avatar");
  const authSection = document.getElementById("auth-section");
  const profileSection = document.getElementById("profile-section");

  const navModerationBtn = document.getElementById("nav-moderation-btn");
  const navFeedBtn = document.getElementById("nav-feed-btn");
  const navPendingBadge = document.getElementById("nav-pending-badge");

  if (user) {
    // Logged in
    if (navLoggedOut) navLoggedOut.classList.add("hidden");
    if (navLoggedIn) navLoggedIn.classList.remove("hidden");
    if (navUserName) navUserName.textContent = user.name;
    if (navUserRole) navUserRole.textContent = user.role;

    if (userToolbar) userToolbar.classList.remove("hidden");
    if (toolbarName) toolbarName.textContent = user.name;
    if (toolbarAvatar) toolbarAvatar.textContent = user.name.charAt(0).toUpperCase();

    if (authSection) authSection.classList.add("hidden");
    if (profileSection) profileSection.classList.remove("hidden");

    // Reveal Moderation Dashboard for admins
    if (user.role === "admin") {
      if (navModerationBtn) navModerationBtn.classList.remove("hidden");
      updatePendingBadge();
    } else {
      if (navModerationBtn) navModerationBtn.classList.add("hidden");
      if (navFeedBtn) navFeedBtn.classList.add("hidden");
      if (navPendingBadge) navPendingBadge.classList.add("hidden");
    }

    // Populate profile card
    const pName = document.getElementById("profile-name");
    const pEmail = document.getElementById("profile-email");
    const pPhone = document.getElementById("profile-phone");
    const pId = document.getElementById("profile-id");
    const pRole = document.getElementById("profile-role");

    if (pName) pName.textContent = user.name;
    if (pEmail) pEmail.textContent = user.email;
    if (pPhone) pPhone.textContent = user.phone_number;
    if (pId) pId.textContent = `#${user.id}`;
    if (pRole) {
      pRole.textContent = user.role;
      if (user.role === "admin") {
        pRole.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-purple-100 text-purple-800";
      } else {
        pRole.className = "px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-blue-100 text-blue-800";
      }
    }
  } else {
    // Logged out
    if (navLoggedOut) navLoggedOut.classList.remove("hidden");
    if (navLoggedIn) navLoggedIn.classList.add("hidden");
    if (navModerationBtn) navModerationBtn.classList.add("hidden");
    if (navFeedBtn) navFeedBtn.classList.add("hidden");
    if (navPendingBadge) navPendingBadge.classList.add("hidden");
    if (userToolbar) userToolbar.classList.add("hidden");
    if (authSection) authSection.classList.remove("hidden");
    if (profileSection) profileSection.classList.add("hidden");
    showView("feed");
  }

  // Refresh items rendering with updated user context
  renderItems(currentItems);
}

// API: Register User
async function registerUser(formData) {
  try {
    const response = await fetch(`${API_BASE}/users/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(formData),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = data.detail || (Array.isArray(data) ? data[0]?.msg : "Registration failed.");
      showBanner(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg), "error");
      return null;
    }

    showBanner(`Account created successfully for ${data.name}! You can now sign in.`, "success");
    showAuthTab("login");
    const loginEmailInput = document.getElementById("login-email");
    if (loginEmailInput) loginEmailInput.value = formData.email;
    return data;
  } catch (error) {
    showBanner(`Network error during registration: ${error.message}`, "error");
    return null;
  }
}

// API: Login User
async function loginUser(email, password) {
  try {
    const response = await fetch(`${API_BASE}/users/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorMsg = data.detail || "Authentication failed. Check your email and password.";
      showBanner(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg), "error");
      return null;
    }

    // Persist session
    localStorage.setItem("auth_token", data.access_token);
    localStorage.setItem("user_data", JSON.stringify(data.user));

    updateAuthUI(data.user);
    showBanner(`Welcome back, ${data.user.name}! You can now post and manage items.`, "success");

    // Fetch items with authentication so own pending items are immediately visible
    await fetchItems();
    return data;
  } catch (error) {
    showBanner(`Network error during login: ${error.message}`, "error");
    return null;
  }
}

// Logout User
function logoutUser() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("user_data");
  updateAuthUI(null);
  fetchItems();
  showBanner("You have been signed out.", "info");
}

// Check session on page load
async function checkSession() {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    updateAuthUI(null);
    return;
  }

  try {
    const response = await fetch(`${API_BASE}/users/me`, {
      method: "GET",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const user = await response.json();
      localStorage.setItem("user_data", JSON.stringify(user));
      updateAuthUI(user);
    } else {
      logoutUser();
    }
  } catch (error) {
    console.error("Session check failed:", error);
    const cachedUser = localStorage.getItem("user_data");
    if (cachedUser) {
      try {
        updateAuthUI(JSON.parse(cachedUser));
      } catch (e) {
        logoutUser();
      }
    } else {
      logoutUser();
    }
  }
}

// --- ITEM MANAGEMENT LOGIC (FR-2 / FR-3 / FR-4) ---

// API: Fetch all items
async function fetchItems() {
  const loadingEl = document.getElementById("items-loading");
  const emptyEl = document.getElementById("items-empty");
  const feedEl = document.getElementById("items-feed");
  if (!feedEl) return;

  if (loadingEl) loadingEl.classList.remove("hidden");
  if (emptyEl) emptyEl.classList.add("hidden");

  try {
    const headers = {};
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/items/`, { headers });
    if (!res.ok) {
      throw new Error(`Failed to load items: HTTP ${res.status}`);
    }
    const items = await res.json();
    currentItems = items;
    renderItems(items);
  } catch (err) {
    console.error("fetchItems error:", err);
    showBanner(`Could not load items: ${err.message}`, "error");
  } finally {
    if (loadingEl) loadingEl.classList.add("hidden");
  }
}

// Render item cards into #items-feed
function renderItems(items) {
  const feedEl = document.getElementById("items-feed");
  const emptyEl = document.getElementById("items-empty");
  if (!feedEl) return;

  feedEl.innerHTML = "";

  if (!items || items.length === 0) {
    if (emptyEl) emptyEl.classList.remove("hidden");
    return;
  }
  if (emptyEl) emptyEl.classList.add("hidden");

  // Determine current active user
  let activeUser = currentUser;
  if (!activeUser) {
    const userJson = localStorage.getItem("user_data");
    if (userJson) {
      try {
        activeUser = JSON.parse(userJson);
      } catch (e) {
        activeUser = null;
      }
    }
  }

  items.forEach((item) => {
    const isOwner = Boolean(activeUser && (String(activeUser.id) === String(item.user_id) || activeUser.role === "admin"));
    const isLost = item.item_type === "lost";
    const typeBadge = isLost
      ? `<span class="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-100 text-rose-700 uppercase tracking-wide">LOST</span>`
      : `<span class="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-700 uppercase tracking-wide">FOUND</span>`;

    const resolvedBadge = item.is_resolved
      ? `<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-200 text-slate-700">✓ Resolved</span>`
      : "";

    // Author View Indicator (FR-4): Moderation status badge and explanation banner
    let moderationBadge = "";
    let moderationInfoBanner = "";

    if (item.status === "pending") {
      moderationBadge = `
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300 space-x-1" title="Pending Admin Review">
          <span>⏳</span>
          <span>Pending Admin Review</span>
        </span>
      `;
      moderationInfoBanner = `
        <div class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start space-x-2.5">
          <span class="text-base flex-shrink-0">⏳</span>
          <div class="flex-1">
            <div class="font-bold text-amber-950 mb-0.5">Pending Admin Review</div>
            <p class="text-amber-800 leading-relaxed">
              This post is currently undergoing the <strong>admin review process</strong>. It is visible only to you and campus administrators. Once approved, it will be published to the public campus feed.
            </p>
          </div>
        </div>
      `;
    } else if (item.status === "rejected") {
      moderationBadge = `
        <button type="button" onclick="viewModerationHistory(${item.id}, '${escapeHtml(item.title)}')" class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300 hover:bg-rose-200 transition space-x-1" title="Click to view rejection comments">
          <span>✕</span>
          <span>Rejected - View Comments</span>
        </button>
      `;
      moderationInfoBanner = `
        <div class="mb-3 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-900 flex items-start space-x-2.5">
          <span class="text-base flex-shrink-0">⚠️</span>
          <div class="flex-1">
            <div class="font-bold text-rose-950 mb-0.5">Post Rejected by Administrator</div>
            <p class="text-rose-800 leading-relaxed mb-1.5">
              This post was not approved during moderation. Click below to view the administrator's review feedback.
            </p>
            <button type="button" onclick="viewModerationHistory(${item.id}, '${escapeHtml(item.title)}')" class="inline-flex items-center px-2.5 py-1 bg-rose-100 hover:bg-rose-200 text-rose-800 rounded font-semibold text-xs border border-rose-200 transition">
              View Rejection Feedback &rarr;
            </button>
          </div>
        </div>
      `;
    } else if (item.status === "approved" && isOwner) {
      moderationBadge = `
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 space-x-1" title="Approved post">
          <span>✓</span>
          <span>Approved</span>
        </span>
      `;
    }

    const dateStr = item.created_at ? new Date(item.created_at).toLocaleDateString() : "";
    const authorName = item.user ? item.user.name : "Student";

    // Photo Gallery Component (FR-3)
    let photosHtml = "";
    if (item.photos && item.photos.length > 0) {
      if (item.photos.length === 1) {
        const photo = item.photos[0];
        photosHtml = `
          <div class="mb-3 rounded-lg overflow-hidden border border-slate-200 bg-slate-100 cursor-pointer group" onclick="openPhotoPreview('${photo.image_url}', '${escapeHtml(photo.caption || '')}')">
            <img src="${photo.image_url}" alt="${escapeHtml(photo.caption || item.title)}" class="h-44 w-full object-cover group-hover:scale-105 transition-transform duration-200" />
            ${photo.caption ? `<div class="p-2 bg-slate-50 border-t border-slate-100 text-xs text-slate-600 italic truncate">${escapeHtml(photo.caption)}</div>` : ''}
          </div>
        `;
      } else {
        const thumbnails = item.photos.map(p => `
          <div class="cursor-pointer group flex flex-col" onclick="openPhotoPreview('${p.image_url}', '${escapeHtml(p.caption || '')}')">
            <div class="rounded-md overflow-hidden border border-slate-200 bg-slate-100 h-24">
              <img src="${p.image_url}" alt="${escapeHtml(p.caption || item.title)}" class="h-full w-full object-cover group-hover:scale-105 transition-transform duration-200" />
            </div>
            ${p.caption ? `<p class="text-xs text-slate-500 italic mt-1 truncate" title="${escapeHtml(p.caption)}">${escapeHtml(p.caption)}</p>` : ''}
          </div>
        `).join("");
        photosHtml = `
          <div class="mb-3">
            <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
              ${thumbnails}
            </div>
          </div>
        `;
      }
    }

    // Owner action buttons
    let actionButtons = "";
    if (isOwner) {
      const resolveBtn = !item.is_resolved
        ? `<button onclick="markResolved(${item.id})" class="px-2.5 py-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-md border border-emerald-200 transition">Mark Resolved</button>`
        : `<span class="text-xs text-slate-400 italic">Resolved</span>`;

      actionButtons = `
        <div class="pt-3 border-t border-slate-100 flex items-center justify-between mt-3 flex-wrap gap-2">
          <div>${resolveBtn}</div>
          <div class="flex items-center space-x-1.5">
            <button onclick="openUploadPhotoModal(${item.id})" class="px-2.5 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-md border border-indigo-200 transition flex items-center space-x-1" title="Add photo to this item">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
              <span>+ Photo</span>
            </button>
            <button onclick="openEditModal(${item.id})" class="px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 rounded-md border border-slate-200 transition">Edit</button>
          </div>
        </div>
      `;
    }

    const card = document.createElement("div");
    card.className = "bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col justify-between hover:shadow-md transition";
    card.id = `item-card-${item.id}`;
    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div class="flex items-center space-x-2 flex-wrap gap-1">
            ${typeBadge}
            ${resolvedBadge}
            ${moderationBadge}
          </div>
          <span class="text-xs text-slate-400">${escapeHtml(dateStr)}</span>
        </div>

        ${moderationInfoBanner}

        ${photosHtml}

        <h3 class="text-lg font-bold text-slate-900 mb-1 leading-snug">${escapeHtml(item.title)}</h3>

        <div class="flex items-center text-xs text-slate-500 mb-3 space-x-1">
          <svg class="w-3.5 h-3.5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span class="truncate">${escapeHtml(item.campus_location)}</span>
        </div>

        <p class="text-sm text-slate-600 line-clamp-3 mb-3">${escapeHtml(item.description)}</p>
      </div>

      <div>
        <div class="text-xs text-slate-400">
          Posted by <span class="font-medium text-slate-700">${escapeHtml(authorName)}</span>
        </div>
        ${actionButtons}
      </div>
    `;
    feedEl.appendChild(card);
  });
}

// API: Create new item
async function createItem(itemData) {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("You must be signed in to post an item.", "error");
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/items/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(itemData),
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.detail || (Array.isArray(data) ? data[0]?.msg : "Failed to create post.");
      showBanner(typeof msg === "string" ? msg : JSON.stringify(msg), "error");
      return null;
    }

    showBanner(`Successfully posted "${data.title}"! Your post is currently Pending Admin Review as part of the admin review process. It is visible only to you until approved by an administrator.`, "success");
    closeCreateModal();
    await fetchItems();
    return data;
  } catch (err) {
    showBanner(`Network error creating post: ${err.message}`, "error");
    return null;
  }
}

// API: Mark item as resolved
async function markResolved(itemId) {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("You must be signed in to resolve an item.", "error");
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/items/${itemId}/resolve`, {
      method: "PATCH",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    const data = await res.json();
    if (!res.ok) {
      showBanner(data.detail || "Failed to resolve item.", "error");
      return null;
    }

    showBanner(`Marked "${data.title}" as resolved!`, "success");
    await fetchItems();
    return data;
  } catch (err) {
    showBanner(`Network error: ${err.message}`, "error");
    return null;
  }
}

// API: Update item
async function updateItem(itemId, itemData) {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("You must be signed in to edit an item.", "error");
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/items/${itemId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(itemData),
    });

    const data = await res.json();
    if (!res.ok) {
      showBanner(data.detail || "Failed to update item.", "error");
      return null;
    }

    showBanner(`Updated "${data.title}" successfully!`, "success");
    closeEditModal();
    await fetchItems();
    return data;
  } catch (err) {
    showBanner(`Network error: ${err.message}`, "error");
    return null;
  }
}

// API: Upload photo attachment for an item
async function uploadPhoto(itemId, fileOrInput, captionOrInput = "") {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("You must be signed in to upload photos.", "error");
    return null;
  }

  let file = null;
  if (fileOrInput instanceof HTMLInputElement) {
    file = fileOrInput.files && fileOrInput.files[0];
  } else if (fileOrInput instanceof File) {
    file = fileOrInput;
  }

  if (!file) {
    showBanner("Please select an image file to upload.", "error");
    return null;
  }

  let caption = "";
  if (captionOrInput instanceof HTMLInputElement) {
    caption = captionOrInput.value.trim();
  } else if (typeof captionOrInput === "string") {
    caption = captionOrInput.trim();
  }

  // Pre-validate file extension and MIME type
  const allowedMime = ["image/jpeg", "image/png", "image/webp"];
  const allowedExts = [".jpg", ".jpeg", ".png", ".webp"];
  const ext = "." + (file.name.split(".").pop() || "").toLowerCase();

  if (!allowedMime.includes(file.type) && !allowedExts.includes(ext)) {
    showBanner("Unsupported file format. Please upload a JPEG, PNG, or WebP image.", "error");
    return null;
  }

  // Pre-validate file size (5 MB limit)
  const maxBytes = 5 * 1024 * 1024;
  if (file.size > maxBytes) {
    showBanner("File size exceeds maximum allowed limit of 5 MB.", "error");
    return null;
  }

  const formData = new FormData();
  formData.append("file", file);
  if (caption) {
    formData.append("caption", caption);
  }

  try {
    const res = await fetch(`${API_BASE}/items/${itemId}/photos`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.detail || (Array.isArray(data) ? data[0]?.msg : "Failed to upload photo.");
      showBanner(typeof msg === "string" ? msg : JSON.stringify(msg), "error");
      return null;
    }

    showBanner("Photo attached successfully!", "success");
    await fetchItems();
    return data;
  } catch (err) {
    showBanner(`Network error uploading photo: ${err.message}`, "error");
    return null;
  }
}

// Upload Photo Modal Handlers
function openUploadPhotoModal(itemId) {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("Please sign in to attach photos.", "info");
    return;
  }

  const form = document.getElementById("upload-photo-form");
  if (form) form.reset();

  const idInput = document.getElementById("upload-photo-item-id");
  if (idInput) idInput.value = itemId;

  const modal = document.getElementById("upload-photo-modal");
  if (modal) {
    modal.classList.remove("hidden");
    modal.style.display = "flex";
  }
}

function closeUploadPhotoModal() {
  const modal = document.getElementById("upload-photo-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal.style.display = "none";
  }
}

async function handleUploadPhotoSubmit(event) {
  event.preventDefault();
  const itemId = parseInt(document.getElementById("upload-photo-item-id").value, 10);
  const fileInput = document.getElementById("upload-photo-file");
  const captionInput = document.getElementById("upload-photo-caption");
  const submitBtn = document.getElementById("upload-photo-submit-btn");

  if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
    showBanner("Please choose an image file to upload.", "error");
    return;
  }

  const file = fileInput.files[0];
  const caption = captionInput ? captionInput.value.trim() : "";

  submitBtn.disabled = true;
  submitBtn.textContent = "Uploading...";
  try {
    const res = await uploadPhoto(itemId, file, caption);
    if (res) {
      closeUploadPhotoModal();
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Upload Photo";
  }
}

// Photo Preview Modal Handlers
function openPhotoPreview(imageUrl, caption) {
  const modal = document.getElementById("photo-preview-modal");
  const imgEl = document.getElementById("preview-modal-img");
  const captionEl = document.getElementById("preview-modal-caption");

  if (!modal || !imgEl) return;

  imgEl.src = imageUrl;
  if (captionEl) {
    if (caption) {
      captionEl.textContent = caption;
      captionEl.classList.remove("hidden");
    } else {
      captionEl.textContent = "";
      captionEl.classList.add("hidden");
    }
  }

  modal.classList.remove("hidden");
  modal.style.display = "flex";
}

function closePhotoPreview() {
  const modal = document.getElementById("photo-preview-modal");
  const imgEl = document.getElementById("preview-modal-img");
  if (modal) {
    modal.classList.add("hidden");
    modal.style.display = "none";
  }
  if (imgEl) {
    imgEl.src = "";
  }
}

// Modal Handlers
function openCreateModal(preselectedType = "lost") {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("Please sign in or create an account to report an item.", "info");
    showAuthTab("login");
    const authSection = document.getElementById("auth-section");
    if (authSection) {
      authSection.classList.remove("hidden");
      authSection.scrollIntoView({ behavior: "smooth" });
    }
    return;
  }

  const form = document.getElementById("create-item-form");
  if (form) {
    form.reset();
    const radio = form.querySelector(`input[name="item_type"][value="${preselectedType}"]`);
    if (radio) radio.checked = true;
  }

  const modal = document.getElementById("create-item-modal");
  if (modal) {
    modal.classList.remove("hidden");
    modal.style.display = "flex";
  }
}

function closeCreateModal() {
  const modal = document.getElementById("create-item-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal.style.display = "none";
  }
}

function openEditModal(itemId) {
  const item = currentItems.find((i) => i.id === itemId);
  if (!item) return;

  document.getElementById("edit-item-id").value = item.id;
  document.getElementById("edit-item-title").value = item.title;
  document.getElementById("edit-item-location").value = item.campus_location;
  document.getElementById("edit-item-description").value = item.description;

  const modal = document.getElementById("edit-item-modal");
  if (modal) {
    modal.classList.remove("hidden");
    modal.style.display = "flex";
  }
}

function closeEditModal() {
  const modal = document.getElementById("edit-item-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal.style.display = "none";
  }
}

// Form Handlers
async function handleCreateItemSubmit(event) {
  event.preventDefault();
  const form = event.target;
  const item_type = form.querySelector('input[name="item_type"]:checked')?.value || "lost";
  const title = document.getElementById("item-title").value.trim();
  const campus_location = document.getElementById("item-location").value.trim();
  const description = document.getElementById("item-description").value.trim();
  const photoInput = document.getElementById("item-photo");
  const captionInput = document.getElementById("item-photo-caption");
  const submitBtn = document.getElementById("create-item-submit-btn");

  if (!title || !campus_location || !description) {
    showBanner("Please fill in all required fields.", "error");
    return;
  }

  // Pre-validate photo if selected
  if (photoInput && photoInput.files && photoInput.files.length > 0) {
    const file = photoInput.files[0];
    const allowedMime = ["image/jpeg", "image/png", "image/webp"];
    const allowedExts = [".jpg", ".jpeg", ".png", ".webp"];
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();

    if (!allowedMime.includes(file.type) && !allowedExts.includes(ext)) {
      showBanner("Unsupported file format. Please upload a JPEG, PNG, or WebP image.", "error");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      showBanner("File size exceeds maximum allowed limit of 5 MB.", "error");
      return;
    }
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Posting...";
  try {
    const newItem = await createItem({
      title,
      campus_location,
      description,
      item_type,
    });

    if (newItem && photoInput && photoInput.files && photoInput.files.length > 0) {
      await uploadPhoto(newItem.id, photoInput.files[0], captionInput ? captionInput.value.trim() : "");
      photoInput.value = "";
      if (captionInput) captionInput.value = "";
      showBanner(`Successfully posted "${newItem.title}" with photo! Your post is currently Pending Admin Review as part of the admin review process.`, "success");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Post Item";
  }
}

async function handleEditItemSubmit(event) {
  event.preventDefault();
  const itemId = parseInt(document.getElementById("edit-item-id").value, 10);
  const title = document.getElementById("edit-item-title").value.trim();
  const campus_location = document.getElementById("edit-item-location").value.trim();
  const description = document.getElementById("edit-item-description").value.trim();
  const submitBtn = document.getElementById("edit-item-submit-btn");

  if (!itemId || !title || !campus_location || !description) {
    showBanner("Please fill in all required fields.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Saving...";
  try {
    await updateItem(itemId, {
      title,
      campus_location,
      description,
    });
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Save Changes";
  }
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;
  const submitBtn = document.getElementById("login-submit-btn");

  if (!email || !password) {
    showBanner("Please fill in both email and password.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Signing In...";
  try {
    await loginUser(email, password);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Sign In";
  }
}

async function handleRegisterSubmit(event) {
  event.preventDefault();
  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const phone_number = document.getElementById("reg-phone").value.trim();
  const password = document.getElementById("reg-password").value;
  const role = document.getElementById("reg-role").value;
  const submitBtn = document.getElementById("register-submit-btn");

  if (!name || !email || !phone_number || !password) {
    showBanner("Please fill in all required fields.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Creating Account...";
  try {
    const res = await registerUser({
      name,
      email,
      phone_number,
      password,
      role,
    });
    if (res) {
      document.getElementById("register-form").reset();
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Create Account";
  }
}

// --- ADMIN MODERATION LOGIC (FR-4 / Step 04) ---

// Switch between Feed view and Moderation view
function showView(view) {
  const feedSection = document.getElementById("feed-section");
  const moderationView = document.getElementById("moderation-view");
  const navFeedBtn = document.getElementById("nav-feed-btn");

  if (view === "moderation") {
    if (feedSection) feedSection.classList.add("hidden");
    if (moderationView) moderationView.classList.remove("hidden");
    if (navFeedBtn) navFeedBtn.classList.remove("hidden");
    loadModerationQueue();
  } else {
    if (feedSection) feedSection.classList.remove("hidden");
    if (moderationView) moderationView.classList.add("hidden");
    if (navFeedBtn) navFeedBtn.classList.add("hidden");
    fetchItems();
  }
}

// Fetch pending item count and update badge in nav
async function updatePendingBadge() {
  const token = localStorage.getItem("auth_token");
  if (!token) return;

  const badge = document.getElementById("nav-pending-badge");
  if (!badge) return;

  try {
    const res = await fetch(`${API_BASE}/moderation/pending`, {
      headers: { "Authorization": `Bearer ${token}` }
    });
    if (res.ok) {
      const items = await res.json();
      if (items.length > 0) {
        badge.textContent = items.length;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
  } catch (e) {
    // Non-critical, ignore
  }
}

// API: Load moderation queue for admin
async function loadModerationQueue() {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("Administrator authorization required.", "error");
    showView("feed");
    return;
  }

  const loadingEl = document.getElementById("moderation-loading");
  const emptyEl = document.getElementById("moderation-empty");
  const queueEl = document.getElementById("moderation-queue-feed");
  const navBadge = document.getElementById("nav-pending-badge");

  if (loadingEl) loadingEl.classList.remove("hidden");
  if (emptyEl) emptyEl.classList.add("hidden");
  if (queueEl) queueEl.innerHTML = "";

  try {
    const res = await fetch(`${API_BASE}/moderation/pending`, {
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      if (res.status === 403) {
        showBanner("Access forbidden: Administrator privileges required.", "error");
        showView("feed");
        return;
      }
      throw new Error(`HTTP ${res.status}`);
    }

    const items = await res.json();

    if (navBadge) {
      if (items.length > 0) {
        navBadge.textContent = items.length;
        navBadge.classList.remove("hidden");
      } else {
        navBadge.classList.add("hidden");
      }
    }

    renderModerationQueue(items);
  } catch (err) {
    console.error("loadModerationQueue error:", err);
    showBanner(`Failed to load moderation queue: ${err.message}`, "error");
  } finally {
    if (loadingEl) loadingEl.classList.add("hidden");
  }
}

// Render cards in the moderation queue
function renderModerationQueue(items) {
  const queueEl = document.getElementById("moderation-queue-feed");
  const emptyEl = document.getElementById("moderation-empty");
  if (!queueEl) return;

  queueEl.innerHTML = "";

  if (!items || items.length === 0) {
    if (emptyEl) emptyEl.classList.remove("hidden");
    return;
  }
  if (emptyEl) emptyEl.classList.add("hidden");

  items.forEach((item) => {
    const isLost = item.item_type === "lost";
    const typeBadge = isLost
      ? `<span class="px-2.5 py-1 text-xs font-bold rounded-full bg-rose-100 text-rose-700 uppercase tracking-wide">LOST</span>`
      : `<span class="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-700 uppercase tracking-wide">FOUND</span>`;

    const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : "";
    const authorName = item.user ? `${item.user.name} (${item.user.email})` : "Student";

    // Photos preview with captions
    let photosHtml = "";
    if (item.photos && item.photos.length > 0) {
      const thumbs = item.photos.map(p => `
        <div class="cursor-pointer group flex flex-col" onclick="openPhotoPreview('${p.image_url}', '${escapeHtml(p.caption || '')}')">
          <div class="rounded-md overflow-hidden border border-slate-200 bg-slate-100 h-24">
            <img src="${p.image_url}" alt="${escapeHtml(p.caption || item.title)}" class="h-full w-full object-cover group-hover:scale-105 transition-transform duration-200" />
          </div>
          ${p.caption ? `<p class="text-xs text-slate-500 italic mt-1 truncate" title="${escapeHtml(p.caption)}">${escapeHtml(p.caption)}</p>` : ''}
        </div>
      `).join("");
      photosHtml = `
        <div class="mb-3">
          <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Attached Photos (${item.photos.length})</div>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">${thumbs}</div>
        </div>
      `;
    }

    const card = document.createElement("div");
    card.className = "bg-white rounded-xl shadow-sm border border-purple-200 p-5 flex flex-col justify-between hover:shadow-md transition-all duration-300";
    card.id = `mod-card-${item.id}`;
    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            ${typeBadge}
            <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Pending Review</span>
          </div>
          <span class="text-xs text-slate-400">${escapeHtml(dateStr)}</span>
        </div>

        <h3 class="text-lg font-bold text-slate-900 mb-1 leading-snug">${escapeHtml(item.title)}</h3>

        <div class="flex items-center text-xs text-slate-500 mb-3 space-x-1">
          <svg class="w-3.5 h-3.5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span class="truncate">${escapeHtml(item.campus_location)}</span>
        </div>

        <p class="text-sm text-slate-600 line-clamp-3 mb-3">${escapeHtml(item.description)}</p>

        ${photosHtml}
      </div>

      <div class="pt-3 border-t border-slate-100 mt-3">
        <div class="text-xs text-slate-400 mb-3">
          Submitted by: <strong class="text-slate-700">${escapeHtml(authorName)}</strong>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="reviewItem(${item.id}, 'approved', 'Post meets community guidelines')" class="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg text-xs shadow flex items-center justify-center space-x-1.5 transition">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            <span>Approve</span>
          </button>
          <button onclick="openRejectModal(${item.id}, '${escapeHtml(item.title)}')" class="flex-1 py-2 px-3 bg-rose-600 hover:bg-rose-700 text-white font-medium rounded-lg text-xs shadow flex items-center justify-center space-x-1.5 transition">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            <span>Reject</span>
          </button>
        </div>
      </div>
    `;
    queueEl.appendChild(card);
  });
}

// API: Review item (Approve or Reject)
async function reviewItem(itemId, decision, comments) {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("Administrator authorization required.", "error");
    return null;
  }

  try {
    const res = await fetch(`${API_BASE}/moderation/${itemId}/review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({ decision, comments }),
    });

    const data = await res.json();
    if (!res.ok) {
      const msg = data.detail || (Array.isArray(data) ? data[0]?.msg : "Moderation review failed.");
      showBanner(typeof msg === "string" ? msg : JSON.stringify(msg), "error");
      return null;
    }

    // Animate removal from moderation queue
    const cardEl = document.getElementById(`mod-card-${itemId}`);
    if (cardEl) {
      cardEl.classList.add("opacity-0", "scale-95");
      setTimeout(() => {
        cardEl.remove();
        const queueEl = document.getElementById("moderation-queue-feed");
        const emptyEl = document.getElementById("moderation-empty");
        if (queueEl && queueEl.children.length === 0 && emptyEl) {
          emptyEl.classList.remove("hidden");
        }
      }, 300);
    }

    const actionText = decision === "approved" ? "Approved post successfully" : "Rejected post";
    showBanner(`${actionText}!`, decision === "approved" ? "success" : "info");

    // Update pending badge and refresh main feed if needed
    updatePendingBadge();
    return data;
  } catch (err) {
    showBanner(`Network error: ${err.message}`, "error");
    return null;
  }
}

// Reject Modal Handlers
function openRejectModal(itemId, title) {
  const idInput = document.getElementById("reject-item-id");
  const titleDisplay = document.getElementById("reject-item-title-display");
  const commentsInput = document.getElementById("reject-comments");

  if (idInput) idInput.value = itemId;
  if (titleDisplay) titleDisplay.textContent = `"${title}"`;
  if (commentsInput) commentsInput.value = "";

  const modal = document.getElementById("reject-item-modal");
  if (modal) {
    modal.classList.remove("hidden");
    modal.style.display = "flex";
  }
}

function closeRejectModal() {
  const modal = document.getElementById("reject-item-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal.style.display = "none";
  }
}

async function handleRejectSubmit(event) {
  event.preventDefault();
  const itemId = parseInt(document.getElementById("reject-item-id").value, 10);
  const comments = document.getElementById("reject-comments").value.trim();
  const submitBtn = document.getElementById("reject-submit-btn");

  if (!comments) {
    showBanner("Rejection comments are required.", "error");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Rejecting...";
  try {
    const res = await reviewItem(itemId, "rejected", comments);
    if (res) {
      closeRejectModal();
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Confirm Rejection";
  }
}

// Moderation History Modal Handlers
async function viewModerationHistory(itemId, itemTitle) {
  const token = localStorage.getItem("auth_token");
  if (!token) {
    showBanner("Please log in to view moderation history.", "info");
    return;
  }

  const modal = document.getElementById("history-modal");
  const titleEl = document.getElementById("history-modal-title");
  const loadingEl = document.getElementById("history-modal-loading");
  const emptyEl = document.getElementById("history-modal-empty");
  const listEl = document.getElementById("history-modal-list");

  if (titleEl) titleEl.textContent = `Moderation Feedback: ${itemTitle}`;
  if (loadingEl) loadingEl.classList.remove("hidden");
  if (emptyEl) emptyEl.classList.add("hidden");
  if (listEl) listEl.innerHTML = "";

  if (modal) {
    modal.classList.remove("hidden");
    modal.style.display = "flex";
  }

  try {
    const res = await fetch(`${API_BASE}/moderation/${itemId}/history`, {
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const history = await res.json();

    if (!history || history.length === 0) {
      if (emptyEl) emptyEl.classList.remove("hidden");
      return;
    }

    listEl.innerHTML = history.map((record) => {
      const isApproved = record.decision === "approved";
      const badge = isApproved
        ? `<span class="px-2 py-0.5 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800">APPROVED</span>`
        : `<span class="px-2 py-0.5 text-xs font-bold rounded-full bg-rose-100 text-rose-800">REJECTED</span>`;
      const dateStr = record.reviewed_at ? new Date(record.reviewed_at).toLocaleString() : "";

      return `
        <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
          <div class="flex items-center justify-between">
            ${badge}
            <span class="text-xs text-slate-400">${escapeHtml(dateStr)}</span>
          </div>
          <div class="text-xs font-medium text-slate-700">Review Comments:</div>
          <div class="text-sm text-slate-600 bg-white p-2.5 rounded border border-slate-100 whitespace-pre-wrap">${escapeHtml(record.comments || "No comments provided.")}</div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.error("viewModerationHistory error:", err);
    if (listEl) listEl.innerHTML = `<p class="text-xs text-rose-600">Failed to load moderation history: ${escapeHtml(err.message)}</p>`;
  } finally {
    if (loadingEl) loadingEl.classList.add("hidden");
  }
}

function closeHistoryModal() {
  const modal = document.getElementById("history-modal");
  if (modal) {
    modal.classList.add("hidden");
    modal.style.display = "none";
  }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", async () => {
  await checkSession();
  await fetchItems();
});
