#!/usr/bin/env bash
# Mirror GitHub Releases (metadata + binary assets) from an upstream repository
# into this repository, byte-for-byte.
#
# This exists because release assets are large (the AstroHybrid packages are
# ~130-200 MB each, ~1.8 GB across all ten releases) and they cannot be moved
# through a developer sandbox: the asset CDN (release-assets.githubusercontent.com)
# and the upload host (uploads.github.com) are usually not reachable from one.
# GitHub Actions runners have normal network access, so the copy runs there.
#
# Usage (normally via .github/workflows/mirror-releases.yml):
#   SRC_REPO=owner/upstream TARGET_REPO=owner/mine TAGS="v1.0.0 v1.0.1" \
#     GITHUB_TOKEN=... ./Tools/release/mirror_releases.sh
#
# Environment:
#   SRC_REPO     upstream repo (default: imnotsharingmyname/pcportastrobot)
#   TARGET_REPO  repo to write into (default: $GITHUB_REPOSITORY)
#   TAGS         space/comma separated tags to mirror (default: every release upstream)
#   DRAFT        true  -> leave mirrored releases as drafts (default: false = publish)
#   OVERWRITE    true  -> re-create existing releases and re-upload assets
#   DRY_RUN      true  -> print the plan, change nothing
#
# Requirements: gh (authenticated), curl, git (with the tags fetched), sha256sum.
set -euo pipefail

SRC_REPO="${SRC_REPO:-imnotsharingmyname/pcportastrobot}"
TARGET_REPO="${TARGET_REPO:-${GITHUB_REPOSITORY:-}}"
DRAFT="${DRAFT:-false}"
OVERWRITE="${OVERWRITE:-false}"
DRY_RUN="${DRY_RUN:-false}"

log()  { printf '%s\n' "==> $*"; }
warn() { printf '%s\n' "warning: $*" >&2; }
die()  { printf '%s\n' "error: $*" >&2; exit 1; }

[[ -n "$TARGET_REPO" ]] || die "TARGET_REPO (or GITHUB_REPOSITORY) must be set"
command -v gh >/dev/null || die "gh is required"
command -v curl >/dev/null || die "curl is required"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated (set GH_TOKEN/GITHUB_TOKEN)"

[[ "$SRC_REPO" != "$TARGET_REPO" ]] || die "SRC_REPO and TARGET_REPO are the same repository"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ---------------------------------------------------------------------------
# Work out which tags to mirror, oldest first, so the newest upstream release
# ends up as "latest" on the target (the launcher's update check relies on it).
# ---------------------------------------------------------------------------
if [[ -n "${TAGS//[ ,]/}" ]]; then
  read -r -a WANTED <<<"${TAGS//,/ }"
else
  mapfile -t WANTED < <(gh api "repos/$SRC_REPO/releases?per_page=100" --paginate \
    --jq '.[] | .tag_name' | tac)
fi
[[ ${#WANTED[@]} -gt 0 ]] || die "no releases found in $SRC_REPO"

log "source:     $SRC_REPO"
log "target:     $TARGET_REPO"
log "tags:       ${WANTED[*]}"
log "draft:      $DRAFT   overwrite: $OVERWRITE   dry-run: $DRY_RUN"

PENDING_PUBLISH=()

for tag in "${WANTED[@]}"; do
  log "--- $tag ---"

  # 1. Fetch upstream release metadata.
  if ! src_json="$(gh api "repos/$SRC_REPO/releases/tags/$tag" 2>/dev/null)"; then
    warn "$tag: no release in $SRC_REPO (tag may not exist) - skipping"
    continue
  fi
  title="$(jq -r '.name // .tag_name' <<<"$src_json")"
  src_prerelease="$(jq -r '.prerelease' <<<"$src_json")"
  mapfile -t asset_ids   < <(jq -r '.assets[].id' <<<"$src_json")
  mapfile -t asset_names < <(jq -r '.assets[].name' <<<"$src_json")
  mapfile -t asset_sizes < <(jq -r '.assets[].size' <<<"$src_json")
  mapfile -t asset_digests < <(jq -r '.assets[] | (.digest // "")' <<<"$src_json")

  printf '%s' "$(jq -r '.body // ""' <<<"$src_json")" > "$WORK_DIR/notes.md"
  log "$tag: \"$title\", ${#asset_ids[@]} asset(s)"

  # 2. Create the release on the target if it is not there yet.
  target_state="$(gh release view "$tag" --repo "$TARGET_REPO" --json isDraft,assets 2>/dev/null || true)"
  targets_exists=false
  if [[ -n "$target_state" ]]; then
    targets_exists=true
    existing_assets="$(jq -r '.assets[]?.name' <<<"$target_state")"
    is_draft="$(jq -r '.isDraft' <<<"$target_state")"
    log "$tag: already on target (draft=$is_draft)"
    if [[ "$is_draft" == "false" && "$OVERWRITE" != "true" ]]; then
      log "$tag: published and OVERWRITE!=true - leaving it alone"
      continue
    fi
  else
    existing_assets=""
  fi

  if [[ "$targets_exists" != "true" ]]; then
    if [[ "$DRY_RUN" == "true" ]]; then
      log "$tag: [dry-run] would create release \"$title\" with ${#asset_ids[@]} asset(s)"
      continue
    fi
    # Resolve the tag to a commit we actually have, so the release points at
    # the same history as upstream (fall back to the default branch).
    target_ref="$(git rev-parse --verify --quiet "refs/tags/$tag^{commit}" || true)"
    [[ -n "$target_ref" ]] || target_ref="$(gh api "repos/$TARGET_REPO" --jq .default_branch)"
    create_args=(release create "$tag" --repo "$TARGET_REPO" --title "$title"
                 --notes-file "$WORK_DIR/notes.md" --draft --target "$target_ref")
    [[ "$src_prerelease" == "true" ]] && create_args+=(--prerelease)
    gh "${create_args[@]}" >/dev/null
    log "$tag: created draft release"
    existing_assets=""
  fi

  # 3. Download and re-upload every asset, verifying upstream size + digest.
  for i in "${!asset_ids[@]}"; do
    name="${asset_names[$i]}"
    id="${asset_ids[$i]}"
    size="${asset_sizes[$i]}"
    digest="${asset_digests[$i]}"
    local_path="$WORK_DIR/$(basename "$name")"

    if grep -Fxq "$name" <<<"$existing_assets" && [[ "$OVERWRITE" != "true" ]]; then
      log "$tag: asset $name already present - skipping"
      continue
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
      log "$tag: [dry-run] would copy $name ($size bytes)"
      continue
    fi

    log "$tag: downloading $name ($size bytes)"
    gh api -H "Accept: application/octet-stream" \
      "repos/$SRC_REPO/releases/assets/$id" > "$local_path"

    actual_size="$(wc -c < "$local_path" | tr -d ' ')"
    [[ "$actual_size" == "$size" ]] \
      || die "$tag: $name size mismatch (expected $size, got $actual_size)"

    if [[ "$digest" == sha256:* ]]; then
      actual_digest="sha256:$(sha256sum "$local_path" | cut -d' ' -f1)"
      [[ "$actual_digest" == "$digest" ]] \
        || die "$tag: $name checksum mismatch (expected $digest, got $actual_digest)"
      log "$tag: $name verified ($digest)"
    else
      warn "$tag: $name has no upstream digest; size verified only"
    fi

    log "$tag: uploading $name"
    gh release upload "$tag" "$local_path" --repo "$TARGET_REPO" --clobber >/dev/null
    rm -f "$local_path"
  done

  [[ "$DRY_RUN" == "true" ]] && continue
  [[ "$DRAFT" == "true" ]] && { log "$tag: left as draft"; continue; }
  PENDING_PUBLISH+=("$tag")
done

# ---------------------------------------------------------------------------
# 4. Publish drafts oldest -> newest and flag the newest as "latest".
# ---------------------------------------------------------------------------
if [[ ${#PENDING_PUBLISH[@]} -gt 0 ]]; then
  newest="${PENDING_PUBLISH[${#PENDING_PUBLISH[@]}-1]}"
  for tag in "${PENDING_PUBLISH[@]}"; do
    edit_args=(release edit "$tag" --repo "$TARGET_REPO" --draft=false)
    [[ "$tag" == "$newest" ]] && edit_args+=(--latest)
    gh "${edit_args[@]}" >/dev/null
    if [[ "$tag" == "$newest" ]]; then
      log "$tag: published and marked latest"
    else
      log "$tag: published"
    fi
  done
fi

log "done"
