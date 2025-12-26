<script setup lang="ts">
/**
 * Deck Editor Page
 *
 * Faithful port of XPlanar Track Coordinate Designer
 * Uses the TrackDesigner component which replicates all
 * functionality from the original HTML app.
 */

// Page uses TrackDesigner component which is self-contained
// with localStorage for persistence (matching original behavior)
</script>

<template>
  <div class="deck-editor-page">
    <DeckTrackDesigner />
  </div>
</template>

<style scoped>
.deck-editor-page {
  height: 100%;
  width: 100%;
  /* Counteract layout padding to make TrackDesigner full-bleed */
  margin: calc(-1 * var(--space-4));
  width: calc(100% + 2 * var(--space-4));
  height: calc(100% + 2 * var(--space-4));
}
</style>
