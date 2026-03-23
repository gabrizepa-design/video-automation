#!/usr/bin/env bash
# =============================================================================
# cleanup-temp.sh — Clean temporary video files older than 24 hours
# =============================================================================

TEMP_DIR="${TEMP_VIDEOS_DIR:-/tmp/videos}"
MAX_AGE_HOURS=24
FREED=0

echo "Cleaning temp files older than ${MAX_AGE_HOURS}h in ${TEMP_DIR}..."

for subdir in scenes audio subtitles; do
  dir="${TEMP_DIR}/${subdir}"
  if [ -d "$dir" ]; then
    count=$(find "$dir" -type f -mmin +$((MAX_AGE_HOURS * 60)) | wc -l)
    if [ "$count" -gt 0 ]; then
      size=$(find "$dir" -type f -mmin +$((MAX_AGE_HOURS * 60)) -exec du -cb {} + | tail -1 | awk '{print $1}')
      find "$dir" -type f -mmin +$((MAX_AGE_HOURS * 60)) -delete
      FREED=$((FREED + size))
      echo "  Cleaned $count files from $subdir/ ($(numfmt --to=iec $size 2>/dev/null || echo "${size}B"))"
    else
      echo "  Nothing to clean in $subdir/"
    fi
  fi
done

echo ""
echo "Total freed: $(numfmt --to=iec $FREED 2>/dev/null || echo "${FREED}B")"
echo "Note: temp_videos/final/ is NOT cleaned automatically (manual review recommended)"
