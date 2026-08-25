// Extracts error message from API reponses
export function getErrorMessage(error) {
	// FastAPI validation error.detail can be string (e.g. Post not found)
	if (typeof error.detail === "string") {
		return error.detail; // Returns directly
		// Can also be list of error objs
	} else if (Array.isArray(error.detail)) {
		return error.detail.map((err) => err.msg).join(". "); // Extracts & joins the array messages
	}
	return "An error occurred. Please try again.";
}

// Shows a Bootstrap modal by ID
// Receives modal ID (e.g. "createPostForm")
export function showModal(modalId) {
	// Gets / creates modal
	const modal = bootstrap.Modal.getOrCreateInstance(
		document.getElementById(modalId),
	);
	modal.show(); // Shows modal
	return modal;
}

// Hides a Bootstrap modal by ID
export function hideModal(modalId) {
	// Gets & hides modal if not exist
	const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
	if (modal) modal.hide();
}
