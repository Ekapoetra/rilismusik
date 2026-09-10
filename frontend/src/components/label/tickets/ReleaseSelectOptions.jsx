import React from "react";

// Native options must contain plain text, never inline presentation elements.
export const ReleaseSelectOptions = ({ releases }) => releases.map((release) => {
  const artists = release.display_primary_artists?.join(", ") || release.artist_name || "";
  const label = [release.release_title, artists].filter(Boolean).join(" — ");
  return React.createElement("option", { key: release.id, value: release.id, translate: "no", "data-testid": `support-release-option-${release.id}` }, label);
});