let currentUser = null;
let fetchPromise = null;

export async function getCurrentUser() {
	// Returns the cached user if exists
	if (currentUser) {
		return currentUser;
	}

	// If fetch already in-progress, return that promise instead of starting another req
	// Multi parts of the page might call getCurrentUser at a time, this prevents duplicate API reqs
	if (fetchPromise) {
		return fetchPromise;
	}

	const token = localStorage.getItem("access_token");
	if (!token) {
		return null;
	}

	fetchPromise = (async () => {
		try {
			// Delegates user retrieval to server via /api/users/me instead of hardcoding JS state
			// to validate token legitimacy & get full user info
			const response = await fetch("/api/users/me", {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (response.ok) {
				// Caches response, confirms active sess
				currentUser = await response.json();
				return currentUser;
			}

			// Purges expired token
			localStorage.removeItem("access_token");
			return null;
		} catch (error) {
			// Handles auth failure (401/403)
			console.error("Error fetching current user:", error);
			return null;
		} finally {
			// Resets promise cache after completion, allowing future re-fetches
			// & return a logged out state
			fetchPromise = null;
		}
	})();

	return fetchPromise;
}

export function logout() {
	// Purges local storage token & in-mem cache
	localStorage.removeItem("access_token");
	currentUser = null;
	window.location.href = "/"; // Redirets to home
}

// Helpers
export function getToken() {
	return localStorage.getItem("access_token");
}

export function setToken(token) {
	localStorage.setItem("access_token", token);
}

export function clearUserCache() {
	currentUser = null;
}
