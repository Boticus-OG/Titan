<script setup lang="ts">
/**
 * TrackDesigner - Faithful port of XPlanar Track Coordinate Designer
 *
 * Original: xplanar_track_designer.html
 * Features:
 * - Tile layout with toggle active/empty
 * - Track drawing with snap to grid
 * - Insert/delete points, renumber lines
 * - Save/load configurations
 * - Export coordinates
 */

// Types
interface Tile {
  x: number
  y: number
  row: number
  col: number
  active: boolean
  number: number
  canvasX?: number
  canvasY?: number
  canvasSize?: number
}

interface TrackLine {
  startX: number
  startY: number
  endX: number
  endY: number
}

interface TemplateState {
  type: string | null
  step: number
  data: Record<string, number>
}

type Mode = 'select' | 'toggleTile' | 'draw' | 'insert' | 'deleteTrack' | 'straightTrack' | 'renumber'

// Constants
const TILE_SIZE = 240 // mm
const SCALE = 1 // pixels per mm
const GRID_SIZE = 5 // mm for snapping
const MIN_ZOOM = 0.5
const MAX_ZOOM = 4.0

// State
const canvasRef = ref<HTMLCanvasElement | null>(null)
const tiles = ref<Tile[]>([])
const trackLines = ref<TrackLine[]>([])
const mode = ref<Mode>('select')
const offsetX = ref(50)
const offsetY = ref(50)
const zoomLevel = ref(1.0)

// Grid inputs
const gridRows = ref(3)
const gridCols = ref(4)

// Drawing state
const pendingLineStart = ref<{ x: number; y: number } | null>(null)
const isDragging = ref(false)
const draggingLineIndex = ref(-1)
const draggingEndpoint = ref<'start' | 'end' | ''>('')

// Selection state
const selectedLineIndex = ref(-1)

// Template state
const templateState = ref<TemplateState>({ type: null, step: 0, data: {} })

// Renumber state
const renumberSequence = ref<number[]>([])
const renumberNextNumber = ref(1)

// UI state
const snapToGrid = ref(true)
const showCoordinates = ref(false)
const statusMessage = ref('Ready - Create a tile grid, then draw track points')
const mouseCoords = ref('—')

// Save/Load state
const saveNameInput = ref('')
const currentConfigName = ref<string | null>(null)
const configSelect = ref('')
const savedConfigs = ref<string[]>([])

// Modal state
const showModal = ref(false)
const modalMessage = ref('')
const modalResolve = ref<((value: boolean) => void) | null>(null)

// Track Lines section state
const trackLinesExpanded = ref(false)
const COLLAPSED_TRACK_COUNT = 4

// Computed
const modeText = computed(() => {
  const modes: Record<Mode, string> = {
    'select': 'Select',
    'toggleTile': 'Toggle Tile',
    'draw': 'Drawing Track',
    'insert': 'Insert Point',
    'deleteTrack': 'Delete Track',
    'straightTrack': 'Straight Track Template',
    'renumber': 'Renumber Lines'
  }
  return modes[mode.value] || 'Select'
})

const templateHelp = computed(() => {
  if (mode.value === 'straightTrack') {
    if (templateState.value.step === 0) {
      return 'Step 1: Click start point on a quadrant line'
    } else {
      return 'Step 2: Click end point (horizontal or vertical)'
    }
  }
  return ''
})

const activeTileCount = computed(() => tiles.value.filter(t => t.active).length)

const visibleTrackLines = computed(() => {
  if (trackLinesExpanded.value || trackLines.value.length <= COLLAPSED_TRACK_COUNT) {
    return trackLines.value
  }
  return trackLines.value.slice(0, COLLAPSED_TRACK_COUNT)
})

const hiddenTrackCount = computed(() => {
  if (trackLinesExpanded.value) return 0
  return Math.max(0, trackLines.value.length - COLLAPSED_TRACK_COUNT)
})

// Methods

function updateStatus(message: string) {
  statusMessage.value = message
}

function openModal(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    modalResolve.value = resolve
    modalMessage.value = message
    showModal.value = true
  })
}

function closeModal(confirmed: boolean) {
  showModal.value = false
  if (modalResolve.value) {
    modalResolve.value(confirmed)
    modalResolve.value = null
  }
}

function setMode(newMode: Mode) {
  // Toggle mode - if clicking same mode, turn it off and return to select
  if (mode.value === newMode) {
    mode.value = 'select'
    newMode = 'select'
  } else {
    mode.value = newMode
  }

  // Clear selection when changing modes (except when entering select mode)
  if (newMode !== 'select') {
    selectedLineIndex.value = -1
  }

  // Reset template state when changing modes
  if (newMode !== 'straightTrack') {
    templateState.value = { type: null, step: 0, data: {} }
  }

  // Reset pending line start when leaving draw mode
  if (newMode !== 'draw') {
    pendingLineStart.value = null
  }

  // Reset renumber state when entering renumber mode
  if (newMode === 'renumber') {
    renumberSequence.value = []
    renumberNextNumber.value = 1
  } else if (mode.value !== 'renumber' && renumberSequence.value.length > 0) {
    applyRenumbering()
  }

  const statusText: Record<Mode, string> = {
    'select': 'Select mode - Click on a line or coordinate card to select it',
    'toggleTile': 'Click tiles to toggle between active/empty',
    'draw': 'Click to add track points',
    'insert': 'Click on a line to insert a point',
    'deleteTrack': 'Click on a line to delete it',
    'straightTrack': 'Click start point on a quadrant line (60mm or 180mm from tile edge)',
    'renumber': `Renumber mode - Click lines to assign new numbers sequentially (Next: ${renumberNextNumber.value})`
  }

  updateStatus(statusText[newMode] || 'Select mode')
  draw()
}

function createTileGrid() {
  tiles.value = []

  // Create tiles from bottom to top (row 0 is bottom)
  for (let r = 0; r < gridRows.value; r++) {
    for (let c = 0; c < gridCols.value; c++) {
      tiles.value.push({
        x: c * TILE_SIZE,
        y: r * TILE_SIZE,
        row: r,
        col: c,
        active: true,
        number: 0
      })
    }
  }

  recalculateTileNumbers()
  updateStatus(`Created ${gridRows.value}x${gridCols.value} tile grid (${activeTileCount.value} active tiles)`)
  draw()
}

function recalculateTileNumbers() {
  let tileNum = 1
  const maxRow = tiles.value.length > 0 ? Math.max(...tiles.value.map(t => t.row)) : 0

  for (let r = 0; r <= maxRow; r++) {
    const rowTiles = tiles.value
      .filter(t => t.row === r)
      .sort((a, b) => a.col - b.col)

    rowTiles.forEach(tile => {
      if (tile.active) {
        tile.number = tileNum++
      } else {
        tile.number = 0
      }
    })
  }

  draw()
}

function clearTiles() {
  tiles.value = []
  trackLines.value = []
  pendingLineStart.value = null
  currentConfigName.value = null
    draw()
  updateStatus('Tiles cleared')
}

async function clearAllTracks() {
  if (trackLines.value.length === 0) {
    updateStatus('No tracks to clear')
    return
  }

  const confirmed = await openModal(`Are you sure you want to delete all ${trackLines.value.length} tracks? This cannot be undone.`)
  if (confirmed) {
    trackLines.value = []
    pendingLineStart.value = null
        draw()
    updateStatus('All tracks cleared')
  }
}

function undoLastPoint() {
  if (pendingLineStart.value) {
    pendingLineStart.value = null
    updateStatus('Cancelled line creation')
  } else if (trackLines.value.length > 0) {
    trackLines.value.pop()
        updateStatus(`Line removed (${trackLines.value.length} lines remaining)`)
  }
  draw()
}

function isPointInActiveTile(x: number, y: number): boolean {
  for (const tile of tiles.value) {
    if (!tile.active) continue

    const tileLeft = tile.x
    const tileRight = tile.x + TILE_SIZE
    const tileBottom = tile.y
    const tileTop = tile.y + TILE_SIZE

    if (x >= tileLeft && x <= tileRight && y >= tileBottom && y <= tileTop) {
      return true
    }
  }
  return false
}

function snapToQuadrantLine(x: number, y: number): { x: number; y: number } {
  const tileX = Math.floor(x / TILE_SIZE)
  const tileY = Math.floor(y / TILE_SIZE)

  const quadLines = [60, 120, 180]

  let snapX = x
  let minDistX = Infinity
  quadLines.forEach(line => {
    const globalX = tileX * TILE_SIZE + line
    const dist = Math.abs(x - globalX)
    if (dist < minDistX) {
      minDistX = dist
      snapX = globalX
    }
  })

  let snapY = y
  let minDistY = Infinity
  quadLines.forEach(line => {
    const globalY = tileY * TILE_SIZE + line
    const dist = Math.abs(y - globalY)
    if (dist < minDistY) {
      minDistY = dist
      snapY = globalY
    }
  })

  return { x: snapX, y: snapY }
}

function distanceToLineSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number) {
  const A = px - x1
  const B = py - y1
  const C = x2 - x1
  const D = y2 - y1

  const dot = A * C + B * D
  const lenSq = C * C + D * D
  let param = -1

  if (lenSq !== 0) {
    param = dot / lenSq
  }

  let xx, yy

  if (param < 0) {
    xx = x1
    yy = y1
  } else if (param > 1) {
    xx = x2
    yy = y2
  } else {
    xx = x1 + param * C
    yy = y1 + param * D
  }

  const dx = px - xx
  const dy = py - yy

  return {
    distance: Math.sqrt(dx * dx + dy * dy),
    closestX: xx,
    closestY: yy,
    param: param
  }
}

function findClickedLine(clickX: number, clickY: number, tolerance = 10) {
  for (let i = 0; i < trackLines.value.length; i++) {
    const line = trackLines.value[i]
    const result = distanceToLineSegment(clickX, clickY, line.startX, line.startY, line.endX, line.endY)

    if (result.distance <= tolerance && result.param > 0.1 && result.param < 0.9) {
      return {
        lineIndex: i,
        insertX: result.closestX,
        insertY: result.closestY
      }
    }
  }
  return null
}

function detectAndAdjustCorners() {
  const CORNER_TOLERANCE = 5
  const CORNER_OFFSET = 10

  for (let i = 0; i < trackLines.value.length; i++) {
    for (let j = i + 1; j < trackLines.value.length; j++) {
      const line1 = trackLines.value[i]
      const line2 = trackLines.value[j]

      const checks = [
        { l1End: 'end', l2End: 'start', l1X: line1.endX, l1Y: line1.endY, l2X: line2.startX, l2Y: line2.startY },
        { l1End: 'end', l2End: 'end', l1X: line1.endX, l1Y: line1.endY, l2X: line2.endX, l2Y: line2.endY },
        { l1End: 'start', l2End: 'start', l1X: line1.startX, l1Y: line1.startY, l2X: line2.startX, l2Y: line2.startY },
        { l1End: 'start', l2End: 'end', l1X: line1.startX, l1Y: line1.startY, l2X: line2.endX, l2Y: line2.endY }
      ]

      checks.forEach(check => {
        const dist = Math.sqrt((check.l1X - check.l2X) ** 2 + (check.l1Y - check.l2Y) ** 2)

        if (dist <= CORNER_TOLERANCE) {
          const line1Angle = check.l1End === 'end'
            ? Math.atan2(line1.endY - line1.startY, line1.endX - line1.startX)
            : Math.atan2(line1.startY - line1.endY, line1.startX - line1.endX)

          const line2Angle = check.l2End === 'end'
            ? Math.atan2(line2.endY - line2.startY, line2.endX - line2.startX)
            : Math.atan2(line2.startY - line2.endY, line2.startX - line2.endX)

          const angleDiff = Math.abs(line1Angle - line2Angle)
          const isPerpendicular = Math.abs(angleDiff - Math.PI/2) < 0.2 || Math.abs(angleDiff - 3*Math.PI/2) < 0.2

          if (isPerpendicular) {
            const cornerX = (check.l1X + check.l2X) / 2
            const cornerY = (check.l1Y + check.l2Y) / 2

            const line1Length = Math.sqrt((line1.endX - line1.startX) ** 2 + (line1.endY - line1.startY) ** 2)
            if (line1Length > CORNER_OFFSET) {
              const line1DirX = (line1.endX - line1.startX) / line1Length
              const line1DirY = (line1.endY - line1.startY) / line1Length

              if (check.l1End === 'end') {
                line1.endX = cornerX - line1DirX * CORNER_OFFSET
                line1.endY = cornerY - line1DirY * CORNER_OFFSET
              } else {
                line1.startX = cornerX + line1DirX * CORNER_OFFSET
                line1.startY = cornerY + line1DirY * CORNER_OFFSET
              }
            }

            const line2Length = Math.sqrt((line2.endX - line2.startX) ** 2 + (line2.endY - line2.startY) ** 2)
            if (line2Length > CORNER_OFFSET) {
              const line2DirX = (line2.endX - line2.startX) / line2Length
              const line2DirY = (line2.endY - line2.startY) / line2Length

              if (check.l2End === 'end') {
                line2.endX = cornerX - line2DirX * CORNER_OFFSET
                line2.endY = cornerY - line2DirY * CORNER_OFFSET
              } else {
                line2.startX = cornerX + line2DirX * CORNER_OFFSET
                line2.startY = cornerY + line2DirY * CORNER_OFFSET
              }
            }
          }
        }
      })
    }
  }
}

function applyRenumbering() {
  if (renumberSequence.value.length === 0) return

  const reorderedLines: TrackLine[] = []

  renumberSequence.value.forEach(oldIdx => {
    reorderedLines.push(trackLines.value[oldIdx])
  })

  trackLines.value.forEach((line, idx) => {
    if (!renumberSequence.value.includes(idx)) {
      reorderedLines.push(line)
    }
  })

  trackLines.value = reorderedLines
  renumberSequence.value = []
  renumberNextNumber.value = 1

    draw()
  updateStatus(`Lines renumbered successfully - ${trackLines.value.length} lines total`)
}

function updateLineCoord(idx: number, coord: keyof TrackLine, value: string) {
  const numValue = parseFloat(value)
  if (isNaN(numValue)) return

  const testLine = { ...trackLines.value[idx] }
  testLine[coord] = numValue

  const isStart = coord === 'startX' || coord === 'startY'
  const x = isStart ? testLine.startX : testLine.endX
  const y = isStart ? testLine.startY : testLine.endY

  if (!isPointInActiveTile(x, y)) {
    updateStatus(`Cannot move ${isStart ? 'start' : 'end'} point outside active tiles`)
    return
  }

  trackLines.value[idx][coord] = numValue
    draw()
  updateStatus(`Line ${idx + 1} updated`)
}

function selectLine(idx: number) {
  if (selectedLineIndex.value === idx) {
    selectedLineIndex.value = -1
    updateStatus('Line deselected')
  } else {
    selectedLineIndex.value = idx
    updateStatus(`Line ${idx + 1} selected`)
  }
  draw()
}

function invertLine(idx: number) {
  const line = trackLines.value[idx]
  const tempStartX = line.startX
  const tempStartY = line.startY

  line.startX = line.endX
  line.startY = line.endY
  line.endX = tempStartX
  line.endY = tempStartY

    draw()
  updateStatus(`Line ${idx + 1} direction inverted`)
}

function deleteLine(idx: number) {
  trackLines.value.splice(idx, 1)
  if (selectedLineIndex.value === idx) {
    selectedLineIndex.value = -1
  } else if (selectedLineIndex.value > idx) {
    selectedLineIndex.value--
  }
    draw()
  updateStatus(`Line ${idx + 1} deleted`)
}

function getLineLength(line: TrackLine): number {
  return Math.sqrt(
    Math.pow(line.endX - line.startX, 2) +
    Math.pow(line.endY - line.startY, 2)
  )
}

// Save/Load functions
function saveConfiguration() {
  let name = saveNameInput.value.trim()

  if (!name && currentConfigName.value) {
    name = currentConfigName.value
  }

  if (!name) {
    updateStatus('Please enter a configuration name')
    return
  }

  const config = {
    tiles: tiles.value,
    trackLines: trackLines.value,
    timestamp: new Date().toISOString()
  }

  try {
    const configs = JSON.parse(localStorage.getItem('xplanarConfigs') || '{}')
    const isUpdate = configs.hasOwnProperty(name)

    configs[name] = config
    localStorage.setItem('xplanarConfigs', JSON.stringify(configs))

    currentConfigName.value = name
    updateConfigDropdown()
    configSelect.value = name
    saveNameInput.value = ''

    if (isUpdate) {
      updateStatus(`Configuration "${name}" updated successfully`)
    } else {
      updateStatus(`Configuration "${name}" saved successfully`)
    }
  } catch (error) {
    updateStatus(`Error saving configuration: ${error}`)
  }
}

function loadConfiguration() {
  const name = configSelect.value

  if (!name) {
    updateStatus('Please select a configuration to load')
    return
  }

  const configs = JSON.parse(localStorage.getItem('xplanarConfigs') || '{}')
  const config = configs[name]

  if (!config) {
    updateStatus('Configuration not found')
    return
  }

  tiles.value = config.tiles
  trackLines.value = config.trackLines
  pendingLineStart.value = null
  currentConfigName.value = name

  recalculateTileNumbers()
    draw()
  updateStatus(`Configuration "${name}" loaded`)
}

async function deleteConfiguration() {
  const name = configSelect.value

  if (!name) {
    updateStatus('Please select a configuration to delete')
    return
  }

  const confirmed = await openModal(`Are you sure you want to delete the configuration "${name}"?\n\nThis action cannot be undone.`)

  if (!confirmed) {
    updateStatus('Delete cancelled')
    return
  }

  try {
    const configs = JSON.parse(localStorage.getItem('xplanarConfigs') || '{}')
    delete configs[name]
    localStorage.setItem('xplanarConfigs', JSON.stringify(configs))

    configSelect.value = ''
    updateConfigDropdown()

    updateStatus(`Configuration "${name}" deleted successfully`)
  } catch (error) {
    updateStatus(`Error deleting configuration: ${error}`)
  }
}

function updateConfigDropdown() {
  const configs = JSON.parse(localStorage.getItem('xplanarConfigs') || '{}')
  savedConfigs.value = Object.keys(configs).sort()
}

function exportConfigFile() {
  const config = {
    version: '1.0',
    name: currentConfigName.value || 'untitled',
    timestamp: new Date().toISOString(),
    tiles: tiles.value,
    trackLines: trackLines.value
  }

  const jsonString = JSON.stringify(config, null, 2)
  const blob = new Blob([jsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
  const filename = `xplanar_${config.name.replace(/[^a-z0-9]/gi, '_')}_${timestamp}.json`

  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  updateStatus(`Configuration exported as ${filename}`)
}

function importConfigFile(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const reader = new FileReader()

  reader.onload = (e) => {
    try {
      const config = JSON.parse(e.target?.result as string)

      if (!config.tiles || !config.trackLines) {
        throw new Error('Invalid configuration file format')
      }

      tiles.value = config.tiles
      trackLines.value = config.trackLines
      pendingLineStart.value = null
      selectedLineIndex.value = -1
      currentConfigName.value = config.name || null

      recalculateTileNumbers()
            draw()

      updateStatus(`Configuration "${config.name}" imported successfully (${trackLines.value.length} lines, ${activeTileCount.value} tiles)`)
    } catch (error) {
      updateStatus(`Error importing file: ${error}`)
      alert(`Error importing configuration:\n\n${error}\n\nPlease check that the file is a valid XPlanar configuration.`)
    }
  }

  reader.onerror = () => {
    updateStatus('Error reading file')
    alert('Error reading file. Please try again.')
  }

  reader.readAsText(file)
  input.value = ''
}

// Sync to Backend (Deck View)
const isSyncing = ref(false)
const API_BASE = 'http://localhost:8000'

async function syncToBackend() {
  if (tiles.value.length === 0) {
    updateStatus('No tiles to sync - create a grid first')
    return
  }

  isSyncing.value = true
  updateStatus('Syncing to backend...')

  try {
    // Determine grid dimensions from tiles
    const maxCol = Math.max(...tiles.value.map(t => t.col))
    const maxRow = Math.max(...tiles.value.map(t => t.row))
    const cols = maxCol + 1
    const rows = maxRow + 1
    const deckHeightMm = rows * TILE_SIZE

    // 1. Resize the grid
    const resizeResponse = await fetch(`${API_BASE}/api/deck/editor/resize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cols, rows })
    })
    if (!resizeResponse.ok) {
      throw new Error(`Resize failed: ${resizeResponse.statusText}`)
    }

    // 2. Sync tile enabled/disabled states
    // DeckView already flips Y when rendering, so we use row indices directly
    // (no row flip needed - DeckView handles the visual transformation)
    for (const tile of tiles.value) {
      const response = await fetch(`${API_BASE}/api/deck/editor/tiles/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          col: tile.col,
          row: tile.row,
          enabled: tile.active
        })
      })
      if (!response.ok) {
        console.warn(`Tile toggle failed for (${tile.col}, ${tile.row}): ${response.statusText}`)
      }
    }

    // 3. Sync track lines
    // DeckView handles Y-flip for display, so we pass coordinates directly
    // (both TD and backend use mm coordinates, just different visual origin)
    const convertedTracks = trackLines.value.map((line, idx) => ({
      track_id: idx + 1,
      name: `Track ${idx + 1}`,
      start_x: line.startX,
      start_y: line.startY,
      end_x: line.endX,
      end_y: line.endY
    }))
    console.log('Tracks ready for backend (when API available):', convertedTracks)

    updateStatus(`Synced to backend: ${cols}x${rows} grid, ${activeTileCount.value} active tiles, ${trackLines.value.length} tracks`)
  } catch (error) {
    updateStatus(`Sync failed: ${error}`)
    console.error('Sync error:', error)
  } finally {
    isSyncing.value = false
  }
}

function generateExportText(): string {
  if (trackLines.value.length === 0) {
    return 'No track lines defined yet'
  }

  let output = 'XPlanar Track Lines\n'
  output += '====================\n\n'
  trackLines.value.forEach((line, idx) => {
    const length = getLineLength(line)
    output += `Line ${idx + 1}:\n`
    output += `  Start:  (${line.startX.toFixed(1)}, ${line.startY.toFixed(1)})\n`
    output += `  End:    (${line.endX.toFixed(1)}, ${line.endY.toFixed(1)})\n`
    output += `  Length: ${length.toFixed(1)}mm\n\n`
  })

  output += '\n--- CSV Format (StartX, StartY, EndX, EndY, Length) ---\n'
  trackLines.value.forEach(line => {
    const length = getLineLength(line)
    output += `${line.startX.toFixed(1)}, ${line.startY.toFixed(1)}, ${line.endX.toFixed(1)}, ${line.endY.toFixed(1)}, ${length.toFixed(1)}\n`
  })

  return output
}

function exportCoordinates() {
  const text = generateExportText()
  if (trackLines.value.length === 0) {
    updateStatus('No track lines to export')
    return
  }
  navigator.clipboard.writeText(text)
  updateStatus(`${trackLines.value.length} track coordinates copied to clipboard!`)
}

// View functions
function resetView() {
  offsetX.value = 50
  offsetY.value = 50
  zoomLevel.value = 1.0
  draw()
  updateStatus('View reset')
}

function centerView() {
  if (tiles.value.length === 0) {
    updateStatus('No tiles to center')
    return
  }

  const canvas = canvasRef.value
  if (!canvas) return

  const maxRow = Math.max(...tiles.value.map(t => t.row))
  const maxCol = Math.max(...tiles.value.map(t => t.col))

  const gridWidth = (maxCol + 1) * TILE_SIZE * zoomLevel.value
  const gridHeight = (maxRow + 1) * TILE_SIZE * zoomLevel.value

  offsetX.value = (canvas.width - gridWidth) / 2
  offsetY.value = (canvas.height - gridHeight) / 2

  draw()
  updateStatus('View centered')
}

function zoomToExtents() {
  if (tiles.value.length === 0) {
    updateStatus('No tiles to zoom to')
    return
  }

  const canvas = canvasRef.value
  if (!canvas) return

  const maxRow = Math.max(...tiles.value.map(t => t.row))
  const maxCol = Math.max(...tiles.value.map(t => t.col))

  const gridWidth = (maxCol + 1) * TILE_SIZE
  const gridHeight = (maxRow + 1) * TILE_SIZE

  const margin = 150
  const availableWidth = canvas.width - (margin * 2)
  const availableHeight = canvas.height - (margin * 2)

  const zoomX = availableWidth / gridWidth
  const zoomY = availableHeight / gridHeight

  zoomLevel.value = Math.min(zoomX, zoomY, MAX_ZOOM)
  zoomLevel.value = Math.max(zoomLevel.value, MIN_ZOOM)

  const scaledWidth = gridWidth * zoomLevel.value
  const scaledHeight = gridHeight * zoomLevel.value

  offsetX.value = (canvas.width - scaledWidth) / 2
  offsetY.value = (canvas.height - scaledHeight) / 2

  draw()
  updateStatus(`Zoomed to extents (${(zoomLevel.value * 100).toFixed(0)}%)`)
}

// Canvas resize
function resizeCanvas() {
  const canvas = canvasRef.value
  const container = canvas?.parentElement
  if (!canvas || !container) return

  canvas.width = container.clientWidth
  canvas.height = container.clientHeight
  draw()
}

// Main draw function
function draw() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const effectiveScale = SCALE * zoomLevel.value

  // Draw background grid (light)
  ctx.strokeStyle = '#ddd'
  ctx.lineWidth = 0.5
  for (let x = 0; x <= 3000; x += GRID_SIZE * effectiveScale) {
    ctx.beginPath()
    ctx.moveTo(offsetX.value + x, 0)
    ctx.lineTo(offsetX.value + x, canvas.height)
    ctx.stroke()
  }
  for (let y = 0; y <= 3000; y += GRID_SIZE * effectiveScale) {
    ctx.beginPath()
    ctx.moveTo(0, offsetY.value + y)
    ctx.lineTo(canvas.width, offsetY.value + y)
    ctx.stroke()
  }

  // Draw tiles
  const maxRow = tiles.value.length > 0 ? Math.max(...tiles.value.map(t => t.row)) : 0

  tiles.value.forEach(tile => {
    const px = offsetX.value + tile.x * effectiveScale
    const py = offsetY.value + (maxRow - tile.row) * TILE_SIZE * effectiveScale
    const size = TILE_SIZE * effectiveScale

    // Tile background
    ctx.fillStyle = tile.active ? '#34495e' : '#e67e22'
    ctx.fillRect(px, py, size, size)

    // Tile border
    ctx.strokeStyle = '#2c3e50'
    ctx.lineWidth = 2
    ctx.strokeRect(px, py, size, size)

    // Quadrant points for active tiles
    if (tile.active) {
      const quadPoints = [
        { x: 60, y: 60, label: 'Q1' },
        { x: 180, y: 60, label: 'Q2' },
        { x: 60, y: 180, label: 'Q3' },
        { x: 180, y: 180, label: 'Q4' },
        { x: 120, y: 120, label: 'C' }
      ]

      quadPoints.forEach(point => {
        const qx = px + point.x * effectiveScale
        const qy = py + (TILE_SIZE - point.y) * effectiveScale

        ctx.fillStyle = point.label === 'C' ? '#e74c3c' : '#27ae60'
        ctx.beginPath()
        const markerSize = Math.max(2, 3 * zoomLevel.value)
        ctx.arc(qx, qy, markerSize, 0, Math.PI * 2)
        ctx.fill()

        ctx.strokeStyle = point.label === 'C' ? '#e74c3c' : '#27ae60'
        ctx.lineWidth = 1
        const crossSize = Math.max(4, 6 * zoomLevel.value)
        ctx.beginPath()
        ctx.moveTo(qx - crossSize, qy)
        ctx.lineTo(qx + crossSize, qy)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(qx, qy - crossSize)
        ctx.lineTo(qx, qy + crossSize)
        ctx.stroke()

        if (zoomLevel.value >= 1.5) {
          ctx.fillStyle = point.label === 'C' ? '#e74c3c' : '#27ae60'
          const labelSize = Math.max(8, 9 * zoomLevel.value)
          ctx.font = `${labelSize}px Arial`
          ctx.textAlign = 'center'
          ctx.fillText(point.label, qx, qy - crossSize - 3)
        }
      })
    }

    // Tile label
    ctx.fillStyle = 'white'
    const fontSize = Math.max(12, 16 * zoomLevel.value)
    ctx.font = `bold ${fontSize}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    if (tile.active) {
      ctx.fillText(`Tile ${tile.number}`, px + size/2, py + size/2)
    } else {
      ctx.fillText('—', px + size/2, py + size/2)
    }

    // Store canvas coordinates for click detection
    tile.canvasX = px
    tile.canvasY = py
    tile.canvasSize = size
  })

  // Draw origin marker
  if (tiles.value.length > 0) {
    const originX = offsetX.value
    const originY = offsetY.value + (maxRow + 1) * TILE_SIZE * effectiveScale

    ctx.strokeStyle = '#e74c3c'
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.moveTo(originX - 20, originY)
    ctx.lineTo(originX + 40, originY)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(originX, originY - 40)
    ctx.lineTo(originX, originY + 20)
    ctx.stroke()

    ctx.fillStyle = '#e74c3c'
    ctx.font = 'bold 14px Arial'
    ctx.textAlign = 'left'
    ctx.fillText('(0,0)', originX + 10, originY + 20)
  }

  // Draw track lines
  if (trackLines.value.length > 0 || pendingLineStart.value) {
    const gridHeight = (maxRow + 1) * TILE_SIZE

    // Detect corners and draw curve zones
    const CORNER_TOLERANCE = 5
    const corners: { x: number; y: number }[] = []

    for (let i = 0; i < trackLines.value.length; i++) {
      for (let j = i + 1; j < trackLines.value.length; j++) {
        const line1 = trackLines.value[i]
        const line2 = trackLines.value[j]

        const checks = [
          { l1X: line1.endX, l1Y: line1.endY, l2X: line2.startX, l2Y: line2.startY },
          { l1X: line1.endX, l1Y: line1.endY, l2X: line2.endX, l2Y: line2.endY },
          { l1X: line1.startX, l1Y: line1.startY, l2X: line2.startX, l2Y: line2.startY },
          { l1X: line1.startX, l1Y: line1.startY, l2X: line2.endX, l2Y: line2.endY }
        ]

        checks.forEach(check => {
          const dist = Math.sqrt((check.l1X - check.l2X) ** 2 + (check.l1Y - check.l2Y) ** 2)
          if (dist <= CORNER_TOLERANCE) {
            corners.push({ x: (check.l1X + check.l2X) / 2, y: (check.l1Y + check.l2Y) / 2 })
          }
        })
      }
    }

    // Draw corner curve zones
    corners.forEach(corner => {
      const px = offsetX.value + corner.x * effectiveScale
      const py = offsetY.value + (gridHeight - corner.y) * effectiveScale

      ctx.fillStyle = 'rgba(241, 196, 15, 0.3)'
      ctx.beginPath()
      ctx.arc(px, py, 10 * effectiveScale, 0, Math.PI * 2)
      ctx.fill()

      ctx.strokeStyle = '#f1c40f'
      ctx.lineWidth = 1
      ctx.stroke()
    })

    // Draw complete lines
    trackLines.value.forEach((line, idx) => {
      const startPx = offsetX.value + line.startX * effectiveScale
      const startPy = offsetY.value + (gridHeight - line.startY) * effectiveScale
      const endPx = offsetX.value + line.endX * effectiveScale
      const endPy = offsetY.value + (gridHeight - line.endY) * effectiveScale

      const isSelected = idx === selectedLineIndex.value

      // Draw highlight for selected
      if (isSelected) {
        ctx.strokeStyle = '#f39c12'
        ctx.lineWidth = 7
        ctx.beginPath()
        ctx.moveTo(startPx, startPy)
        ctx.lineTo(endPx, endPy)
        ctx.stroke()
      }

      // Draw line
      ctx.strokeStyle = '#27ae60'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.moveTo(startPx, startPy)
      ctx.lineTo(endPx, endPy)
      ctx.stroke()

      // Draw points
      const pointRadius = Math.max(4, 6 * zoomLevel.value)

      ctx.fillStyle = isSelected ? '#f39c12' : '#27ae60'
      ctx.beginPath()
      ctx.arc(startPx, startPy, pointRadius * (isSelected ? 1.3 : 1), 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.fillStyle = isSelected ? '#f39c12' : '#e74c3c'
      ctx.beginPath()
      ctx.arc(endPx, endPy, pointRadius * (isSelected ? 1.3 : 1), 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 2
      ctx.stroke()

      // Line number
      const midX = (startPx + endPx) / 2
      const midY = (startPy + endPy) / 2

      let displayNumber = idx + 1
      let numberColor = 'black'
      let bgColor = 'rgba(255, 255, 255, 0.9)'

      if (isSelected) {
        numberColor = 'white'
        bgColor = '#f39c12'
      } else if (mode.value === 'renumber') {
        const renumberIdx = renumberSequence.value.indexOf(idx)
        if (renumberIdx >= 0) {
          displayNumber = renumberIdx + 1
          numberColor = 'white'
          bgColor = '#27ae60'
        } else {
          numberColor = '#95a5a6'
          bgColor = 'rgba(255, 255, 255, 0.7)'
        }
      }

      const labelFontSize = Math.max(10, 12 * zoomLevel.value)
      ctx.font = `bold ${labelFontSize}px Arial`
      ctx.textAlign = 'center'

      const textWidth = ctx.measureText(`Line ${displayNumber}`).width
      const padding = 6
      ctx.fillStyle = bgColor
      ctx.beginPath()
      ctx.roundRect(midX - textWidth/2 - padding, midY - labelFontSize/2 - padding - 10 * zoomLevel.value,
                    textWidth + padding * 2, labelFontSize + padding * 2, 4)
      ctx.fill()

      ctx.fillStyle = numberColor
      ctx.fillText(`Line ${displayNumber}`, midX, midY - 10 * zoomLevel.value + labelFontSize/2)

      // Show coordinates if enabled or selected
      if (showCoordinates.value || (isDragging.value && draggingLineIndex.value === idx) || isSelected) {
        const coordText = `Line ${displayNumber}: (${line.startX.toFixed(1)}, ${line.startY.toFixed(1)}) → (${line.endX.toFixed(1)}, ${line.endY.toFixed(1)})`
        const coordFontSize = Math.max(9, 11 * zoomLevel.value)
        ctx.font = `${coordFontSize}px Arial`
        ctx.textAlign = 'left'

        const coordTextWidth = ctx.measureText(coordText).width
        ctx.fillStyle = isSelected ? '#f39c12' : 'rgba(255, 255, 255, 0.9)'
        ctx.fillRect(midX + 10 * zoomLevel.value, midY + 5 * zoomLevel.value, coordTextWidth + 8, coordFontSize + 8)

        ctx.fillStyle = isSelected ? 'white' : '#2c3e50'
        ctx.fillText(coordText, midX + 10 * zoomLevel.value + 4, midY + 5 * zoomLevel.value + coordFontSize)
      }
    })

    // Draw pending line start
    if (pendingLineStart.value) {
      const startPx = offsetX.value + pendingLineStart.value.x * effectiveScale
      const startPy = offsetY.value + (gridHeight - pendingLineStart.value.y) * effectiveScale

      const pointRadius = Math.max(4, 6 * zoomLevel.value)
      ctx.fillStyle = '#f39c12'
      ctx.beginPath()
      ctx.arc(startPx, startPy, pointRadius, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.fillStyle = '#f39c12'
      const fontSize = Math.max(10, 12 * zoomLevel.value)
      ctx.font = `bold ${fontSize}px Arial`
      ctx.textAlign = 'center'
      ctx.fillText('Start', startPx, startPy - 15 * zoomLevel.value)
    }

    // Draw template start point
    if (mode.value === 'straightTrack' && templateState.value.step === 1) {
      const startPx = offsetX.value + templateState.value.data.startX * effectiveScale
      const startPy = offsetY.value + (gridHeight - templateState.value.data.startY) * effectiveScale

      const pointRadius = Math.max(4, 6 * zoomLevel.value)
      ctx.fillStyle = '#9b59b6'
      ctx.beginPath()
      ctx.arc(startPx, startPy, pointRadius, 0, Math.PI * 2)
      ctx.fill()
      ctx.strokeStyle = 'white'
      ctx.lineWidth = 2
      ctx.stroke()

      ctx.fillStyle = '#9b59b6'
      const fontSize = Math.max(10, 12 * zoomLevel.value)
      ctx.font = `bold ${fontSize}px Arial`
      ctx.textAlign = 'center'
      ctx.fillText('Template Start', startPx, startPy - 15 * zoomLevel.value)
    }
  }
}

// Event handlers
function handleCanvasClick(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const clickX = e.clientX - rect.left
  const clickY = e.clientY - rect.top
  const effectiveScale = SCALE * zoomLevel.value

  // Check tile click in toggleTile mode
  if (mode.value === 'toggleTile' && tiles.value.length > 0) {
    for (const tile of tiles.value) {
      if (tile.canvasX !== undefined && tile.canvasY !== undefined && tile.canvasSize !== undefined) {
        if (clickX >= tile.canvasX && clickX <= tile.canvasX + tile.canvasSize &&
            clickY >= tile.canvasY && clickY <= tile.canvasY + tile.canvasSize) {
          tile.active = !tile.active
          recalculateTileNumbers()
          updateStatus(`Tile ${tile.active ? 'activated' : 'deactivated'} - ${activeTileCount.value} active tiles`)
          return
        }
      }
    }
  }

  if (tiles.value.length === 0) return

  const maxRow = Math.max(...tiles.value.map(t => t.row))
  const gridHeight = (maxRow + 1) * TILE_SIZE

  let x = (clickX - offsetX.value) / effectiveScale
  let y = gridHeight - ((clickY - offsetY.value) / effectiveScale)

  // Handle insert mode
  if (mode.value === 'insert') {
    const clickedLine = findClickedLine(x, y, 15)

    if (clickedLine) {
      const lineIdx = clickedLine.lineIndex
      const insertX = clickedLine.insertX
      const insertY = clickedLine.insertY

      const originalLine = trackLines.value[lineIdx]

      const newLine1: TrackLine = {
        startX: originalLine.startX,
        startY: originalLine.startY,
        endX: insertX,
        endY: insertY
      }

      const newLine2: TrackLine = {
        startX: insertX,
        startY: insertY,
        endX: originalLine.endX,
        endY: originalLine.endY
      }

      trackLines.value.splice(lineIdx, 1, newLine1, newLine2)

      detectAndAdjustCorners()
            draw()

      updateStatus(`Point inserted at (${insertX.toFixed(1)}, ${insertY.toFixed(1)}) - Line ${lineIdx + 1} split`)
    } else {
      updateStatus('Click on a line to insert a point (not near endpoints)')
    }
    return
  }

  // Handle delete track mode
  if (mode.value === 'deleteTrack') {
    const clickedLine = findClickedLine(x, y, 15)

    if (clickedLine) {
      const lineIdx = clickedLine.lineIndex
      trackLines.value.splice(lineIdx, 1)

      detectAndAdjustCorners()
            draw()

      updateStatus(`Line ${lineIdx + 1} deleted - ${trackLines.value.length} lines remaining`)
    } else {
      updateStatus('Click on a line to delete it')
    }
    return
  }

  // Handle renumber mode
  if (mode.value === 'renumber') {
    const clickedLine = findClickedLine(x, y, 15)

    if (clickedLine) {
      const lineIdx = clickedLine.lineIndex

      if (renumberSequence.value.includes(lineIdx)) {
        updateStatus(`Line ${lineIdx + 1} already assigned as Line ${renumberSequence.value.indexOf(lineIdx) + 1}`)
        return
      }

      renumberSequence.value.push(lineIdx)
      renumberNextNumber.value++

      draw()
      updateStatus(`Line ${lineIdx + 1} → Line ${renumberSequence.value.length} (Next: ${renumberNextNumber.value})`)
    } else {
      updateStatus('Click on a line to renumber it')
    }
    return
  }

  // Handle select mode
  if (mode.value === 'select') {
    const clickedLine = findClickedLine(x, y, 15)

    if (clickedLine) {
      const lineIdx = clickedLine.lineIndex

      if (selectedLineIndex.value === lineIdx) {
        selectedLineIndex.value = -1
        updateStatus('Line deselected')
      } else {
        selectedLineIndex.value = lineIdx
        updateStatus(`Line ${lineIdx + 1} selected`)
      }

      draw()
    } else {
      if (selectedLineIndex.value !== -1) {
        selectedLineIndex.value = -1
        updateStatus('Selection cleared')
        draw()
      }
    }
    return
  }

  // Handle straight track template mode
  if (mode.value === 'straightTrack') {
    const snapped = snapToQuadrantLine(x, y)
    x = snapped.x
    y = snapped.y

    if (!isPointInActiveTile(x, y)) {
      updateStatus('Cannot add point outside active tiles')
      return
    }

    if (templateState.value.step === 0) {
      templateState.value.data.startX = x
      templateState.value.data.startY = y
      templateState.value.step = 1
      updateStatus(`Start point: (${x.toFixed(1)}, ${y.toFixed(1)}) - Click end point`)
      draw()
    } else if (templateState.value.step === 1) {
      const startX = templateState.value.data.startX
      const startY = templateState.value.data.startY

      const deltaX = Math.abs(x - startX)
      const deltaY = Math.abs(y - startY)

      if (deltaX > deltaY) {
        y = startY
      } else {
        x = startX
      }

      if (Math.abs(x - startX) < 5 && Math.abs(y - startY) < 5) {
        updateStatus('Start and end points too close - try again')
        return
      }

      trackLines.value.push({
        startX: startX,
        startY: startY,
        endX: x,
        endY: y
      })

      detectAndAdjustCorners()
            draw()

      templateState.value = { type: null, step: 0, data: {} }
      updateStatus(`Straight track created: (${startX.toFixed(1)}, ${startY.toFixed(1)}) → (${x.toFixed(1)}, ${y.toFixed(1)})`)
    }
    return
  }

  // Handle normal draw mode
  if (mode.value !== 'draw') return

  if (snapToGrid.value) {
    x = Math.round(x / GRID_SIZE) * GRID_SIZE
    y = Math.round(y / GRID_SIZE) * GRID_SIZE
  }

  if (!isPointInActiveTile(x, y)) {
    updateStatus('Cannot add point outside active tiles')
    return
  }

  if (!pendingLineStart.value) {
    pendingLineStart.value = { x, y }
    updateStatus(`Line ${trackLines.value.length + 1} started at (${x.toFixed(1)}, ${y.toFixed(1)}) - Click to set end point`)
    draw()
  } else {
    trackLines.value.push({
      startX: pendingLineStart.value.x,
      startY: pendingLineStart.value.y,
      endX: x,
      endY: y
    })
    pendingLineStart.value = null

    detectAndAdjustCorners()
        draw()
    updateStatus(`Line ${trackLines.value.length} created`)
  }
}

function handleCanvasMouseMove(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const maxRow = tiles.value.length > 0 ? Math.max(...tiles.value.map(t => t.row)) : 0
  const gridHeight = (maxRow + 1) * TILE_SIZE
  const effectiveScale = SCALE * zoomLevel.value

  let x = (e.clientX - rect.left - offsetX.value) / effectiveScale
  let y = gridHeight - ((e.clientY - rect.top - offsetY.value) / effectiveScale)

  // Handle dragging
  if (isDragging.value && draggingLineIndex.value >= 0) {
    if (snapToGrid.value) {
      x = Math.round(x / GRID_SIZE) * GRID_SIZE
      y = Math.round(y / GRID_SIZE) * GRID_SIZE
    }

    if (isPointInActiveTile(x, y)) {
      if (draggingEndpoint.value === 'start') {
        trackLines.value[draggingLineIndex.value].startX = x
        trackLines.value[draggingLineIndex.value].startY = y
      } else if (draggingEndpoint.value === 'end') {
        trackLines.value[draggingLineIndex.value].endX = x
        trackLines.value[draggingLineIndex.value].endY = y
      }
            draw()
    }
    return
  }

  // Normal mouse move
  if (snapToGrid.value) {
    x = Math.round(x / GRID_SIZE) * GRID_SIZE
    y = Math.round(y / GRID_SIZE) * GRID_SIZE
  }

  mouseCoords.value = `X: ${x.toFixed(1)}mm, Y: ${y.toFixed(1)}mm`
}

function handleCanvasMouseDown(e: MouseEvent) {
  // Only allow dragging with right mouse button
  if (e.button !== 2) return
  if (mode.value !== 'draw' || trackLines.value.length === 0) return

  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  const maxRow = tiles.value.length > 0 ? Math.max(...tiles.value.map(t => t.row)) : 0
  const gridHeight = (maxRow + 1) * TILE_SIZE
  const effectiveScale = SCALE * zoomLevel.value

  for (let i = 0; i < trackLines.value.length; i++) {
    const line = trackLines.value[i]

    const startPx = offsetX.value + line.startX * effectiveScale
    const startPy = offsetY.value + (gridHeight - line.startY) * effectiveScale
    const distStart = Math.sqrt((mouseX - startPx) ** 2 + (mouseY - startPy) ** 2)

    if (distStart <= 10) {
      isDragging.value = true
      draggingLineIndex.value = i
      draggingEndpoint.value = 'start'
      updateStatus(`Dragging Line ${i + 1} start point`)
      e.preventDefault()
      return
    }

    const endPx = offsetX.value + line.endX * effectiveScale
    const endPy = offsetY.value + (gridHeight - line.endY) * effectiveScale
    const distEnd = Math.sqrt((mouseX - endPx) ** 2 + (mouseY - endPy) ** 2)

    if (distEnd <= 10) {
      isDragging.value = true
      draggingLineIndex.value = i
      draggingEndpoint.value = 'end'
      updateStatus(`Dragging Line ${i + 1} end point`)
      e.preventDefault()
      return
    }
  }
}

function handleCanvasMouseUp() {
  if (isDragging.value) {
    const line = trackLines.value[draggingLineIndex.value]

    detectAndAdjustCorners()
        draw()

    const coord = draggingEndpoint.value === 'start'
      ? `(${line.startX.toFixed(1)}, ${line.startY.toFixed(1)})`
      : `(${line.endX.toFixed(1)}, ${line.endY.toFixed(1)})`
    updateStatus(`Line ${draggingLineIndex.value + 1} ${draggingEndpoint.value} moved to ${coord}`)

    isDragging.value = false
    draggingLineIndex.value = -1
    draggingEndpoint.value = ''
  }
}

function handleCanvasWheel(e: WheelEvent) {
  e.preventDefault()

  const canvas = canvasRef.value
  if (!canvas) return

  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9
  const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomLevel.value * zoomFactor))

  const zoomRatio = newZoom / zoomLevel.value
  offsetX.value = mouseX - (mouseX - offsetX.value) * zoomRatio
  offsetY.value = mouseY - (mouseY - offsetY.value) * zoomRatio

  zoomLevel.value = newZoom
  draw()
  updateStatus(`Zoom: ${(zoomLevel.value * 100).toFixed(0)}%`)
}

function handleCanvasContextMenu(e: MouseEvent) {
  e.preventDefault()
}

// Native scroll handles sidebar - no custom handler needed

// Auto-save current session to localStorage
const SESSION_KEY = 'xplanarCurrentSession'

function saveSession() {
  if (tiles.value.length === 0 && trackLines.value.length === 0) return

  const session = {
    tiles: tiles.value,
    trackLines: trackLines.value,
    gridRows: gridRows.value,
    gridCols: gridCols.value,
    currentConfigName: currentConfigName.value,
    timestamp: new Date().toISOString()
  }
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
}

function loadSession() {
  try {
    const saved = localStorage.getItem(SESSION_KEY)
    if (!saved) return false

    const session = JSON.parse(saved)
    if (session.tiles && session.tiles.length > 0) {
      tiles.value = session.tiles
      trackLines.value = session.trackLines || []
      gridRows.value = session.gridRows || 3
      gridCols.value = session.gridCols || 4
      currentConfigName.value = session.currentConfigName || null
      recalculateTileNumbers()
      updateStatus(`Session restored (${tiles.value.length} tiles, ${trackLines.value.length} tracks)`)
      return true
    }
  } catch (e) {
    console.warn('Failed to load session:', e)
  }
  return false
}

// Lifecycle
onMounted(() => {
  updateConfigDropdown()

  // Try to restore last session
  const restored = loadSession()

  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)

  if (!restored) {
    updateStatus('Ready - Create a tile grid, then draw track points')
  }
})

onUnmounted(() => {
  // Auto-save session before leaving
  saveSession()
  window.removeEventListener('resize', resizeCanvas)
})
</script>

<template>
  <div class="track-designer">
    <div class="sidebar">
      <h2 class="sidebar-title">XPlanar Track Designer</h2>

      <!-- 1. Tile Layout Section -->
      <div class="section">
        <h3>Tile Layout</h3>
        <div class="grid-input">
          <label>Rows:</label>
          <input v-model.number="gridRows" type="number" min="1" max="20">
        </div>
        <div class="grid-input">
          <label>Cols:</label>
          <input v-model.number="gridCols" type="number" min="1" max="20">
        </div>
        <button class="btn" @click="createTileGrid">Create Grid</button>
        <button class="btn" @click="clearTiles">Clear Tiles</button>
        <button class="btn" :class="{ active: mode === 'toggleTile' }" @click="setMode('toggleTile')">Toggle Tile</button>
        <div class="legend">
          <label class="legend-title">Tile states:</label>
          <div class="legend-items">
            <div class="legend-item">
              <div class="legend-swatch" style="background: #34495e;"></div>
              <span class="legend-label">Active Tile</span>
            </div>
            <div class="legend-item">
              <div class="legend-swatch" style="background: #e67e22;"></div>
              <span class="legend-label">Empty Space</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 2. Drawing Tools Section (merged Track Drawing + Track Templates) -->
      <div class="section">
        <h3>Drawing Tools</h3>
        <button class="btn" :class="{ active: mode === 'draw' }" @click="setMode('draw')">Draw Track</button>
        <button class="btn" :class="{ active: mode === 'straightTrack' }" @click="setMode('straightTrack')">Straight Track</button>
        <button class="btn" :class="{ active: mode === 'insert' }" @click="setMode('insert')">Insert Point</button>
        <button class="btn" :class="{ active: mode === 'deleteTrack' }" @click="setMode('deleteTrack')">Delete Track</button>
        <button class="btn" :class="{ active: mode === 'renumber' }" @click="setMode('renumber')">Renumber Lines</button>
        <button class="btn" @click="clearAllTracks">Clear All Tracks</button>
        <button class="btn" @click="undoLastPoint">Undo Point</button>
        <div v-if="templateHelp" class="template-help">{{ templateHelp }}</div>
        <div class="checkbox-row">
          <label>
            <input v-model="snapToGrid" type="checkbox"> Snap to Grid (5mm)
          </label>
        </div>
        <div class="checkbox-row">
          <label>
            <input v-model="showCoordinates" type="checkbox" @change="draw"> Show Coordinates
          </label>
        </div>
      </div>

      <!-- 3. Save/Load Section -->
      <div class="section">
        <h3>Save/Load</h3>
        <div class="save-section">
          <label class="section-label">Save Current Configuration:</label>
          <input
            v-model="saveNameInput"
            type="text"
            class="save-input"
            placeholder="Enter new name or leave blank to update..."
          >
          <button class="btn" @click="saveConfiguration">
            {{ currentConfigName ? `Update "${currentConfigName}"` : 'Save Configuration' }}
          </button>
          <div v-if="currentConfigName" class="current-config">
            Active: <span class="config-name">{{ currentConfigName }}</span>
          </div>
        </div>
        <div class="load-section">
          <label class="section-label">Load Configuration:</label>
          <select v-model="configSelect" class="config-select">
            <option value="">-- Select Configuration --</option>
            <option v-for="name in savedConfigs" :key="name" :value="name">{{ name }}</option>
          </select>
          <div class="load-buttons">
            <button class="btn" @click="loadConfiguration">Load</button>
            <button class="btn btn-danger" @click="deleteConfiguration">Delete</button>
          </div>
        </div>
        <div class="export-section">
          <label class="section-label">Export/Import File:</label>
          <div class="export-buttons">
            <button class="btn btn-purple" @click="exportConfigFile">Export File</button>
            <button class="btn btn-teal" @click="($refs.importInput as HTMLInputElement).click()">Import File</button>
          </div>
          <input ref="importInput" type="file" accept=".json" style="display: none;" @change="importConfigFile">
          <div class="export-hint">Export/import configuration as .json file</div>
        </div>
      </div>

      <!-- 4. Export Coordinates Section (button only, no text area) -->
      <div class="section">
        <h3>Export Coordinates</h3>
        <button class="btn btn-export" @click="exportCoordinates">Copy to Clipboard</button>
      </div>

      <!-- 5. Sync to Deck Section -->
      <div class="section">
        <h3>Sync to Deck</h3>
        <button
          class="btn btn-sync"
          :disabled="isSyncing || tiles.length === 0"
          @click="syncToBackend"
        >
          {{ isSyncing ? 'Syncing...' : 'Push to Deck View' }}
        </button>
        <div class="sync-hint">Push tile layout and tracks to the live Deck view</div>
      </div>

      <!-- 6. Track Lines Section (collapsible, always last) -->
      <div class="section section-track-lines">
        <h3 class="section-header-collapsible" @click="trackLinesExpanded = !trackLinesExpanded">
          <span class="expand-icon">{{ trackLinesExpanded ? '▼' : '▶' }}</span>
          Track Lines ({{ trackLines.length }})
        </h3>
        <div class="point-list">
          <div
            v-for="(line, idx) in visibleTrackLines"
            :key="idx"
            class="point-item"
            :class="{ selected: idx === selectedLineIndex }"
            @click="mode === 'select' && selectLine(idx)"
          >
            <div class="point-info">
              <div class="point-header">
                <span class="point-label" :class="{ selected: idx === selectedLineIndex }">Line {{ idx + 1 }}:</span>
                <span class="point-length">Length: {{ getLineLength(line).toFixed(1) }}mm</span>
              </div>
              <div class="point-coords">
                <span class="coord-label">Start:</span>
                <input
                  type="number"
                  step="0.1"
                  :value="line.startX.toFixed(1)"
                  @change="(e) => updateLineCoord(idx, 'startX', (e.target as HTMLInputElement).value)"
                  @click.stop
                >
                <input
                  type="number"
                  step="0.1"
                  :value="line.startY.toFixed(1)"
                  @change="(e) => updateLineCoord(idx, 'startY', (e.target as HTMLInputElement).value)"
                  @click.stop
                >
              </div>
              <div class="point-coords">
                <span class="coord-label">End:</span>
                <input
                  type="number"
                  step="0.1"
                  :value="line.endX.toFixed(1)"
                  @change="(e) => updateLineCoord(idx, 'endX', (e.target as HTMLInputElement).value)"
                  @click.stop
                >
                <input
                  type="number"
                  step="0.1"
                  :value="line.endY.toFixed(1)"
                  @change="(e) => updateLineCoord(idx, 'endY', (e.target as HTMLInputElement).value)"
                  @click.stop
                >
              </div>
            </div>
            <div class="point-actions">
              <button class="btn-invert" @click.stop="invertLine(idx)" title="Invert line direction">&#8644;</button>
              <button class="btn-delete" @click.stop="deleteLine(idx)">X</button>
            </div>
          </div>
          <!-- Show more indicator -->
          <div v-if="hiddenTrackCount > 0" class="show-more" @click="trackLinesExpanded = true">
            + {{ hiddenTrackCount }} more tracks (click to expand)
          </div>
          <!-- Collapse indicator when expanded -->
          <div v-if="trackLinesExpanded && trackLines.length > COLLAPSED_TRACK_COUNT" class="show-less" @click="trackLinesExpanded = false">
            ▲ Collapse
          </div>
        </div>
      </div>
    </div>

    <div class="main-area">
      <div class="toolbar">
        <span>Mode: <span class="mode-indicator">{{ modeText }}</span></span>
        <button class="btn toolbar-btn" @click="centerView">Center View</button>
        <button class="btn toolbar-btn" @click="zoomToExtents">Zoom Extents</button>
        <span class="toolbar-spacer"></span>
        <span>Mouse: <span class="mouse-coords">{{ mouseCoords }}</span></span>
        <button class="btn toolbar-btn" @click="resetView">Reset View</button>
      </div>
      <div class="canvas-container">
        <canvas
          ref="canvasRef"
          @click="handleCanvasClick"
          @mousemove="handleCanvasMouseMove"
          @mousedown="handleCanvasMouseDown"
          @mouseup="handleCanvasMouseUp"
          @wheel="handleCanvasWheel"
          @contextmenu="handleCanvasContextMenu"
        ></canvas>
      </div>
      <div class="status-bar">{{ statusMessage }}</div>
    </div>

    <!-- Confirmation Modal -->
    <div v-if="showModal" class="modal">
      <div class="modal-content">
        <div class="modal-title">Confirm Delete</div>
        <div class="modal-message">{{ modalMessage }}</div>
        <div class="modal-buttons">
          <button class="modal-btn modal-btn-cancel" @click="closeModal(false)">Cancel</button>
          <button class="modal-btn modal-btn-confirm" @click="closeModal(true)">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.track-designer {
  display: flex;
  height: 100%;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f0f0f0;
  overflow: hidden;
}

.sidebar {
  width: 320px;
  min-width: 250px;
  max-width: 500px;
  height: 100%;
  min-height: 0; /* Flexbox fix: allows shrinking below content size */
  flex-shrink: 0;
  background: #2c3e50;
  color: white;
  padding: 20px;
  overflow-y: auto;
  resize: horizontal;
  position: relative;
  box-sizing: border-box;
}

.sidebar::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: #34495e;
  cursor: ew-resize;
}

.sidebar::-webkit-scrollbar {
  display: none;
}

.sidebar-title {
  margin-bottom: 20px;
  color: #3498db;
}

.section {
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #34495e;
}

.section:last-child {
  border-bottom: none;
}

.section h3 {
  margin-bottom: 15px;
  color: #3498db;
  font-size: 15px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 10px 15px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  width: 100%;
  margin-bottom: 8px;
  transition: background 0.2s;
}

.btn:hover {
  background: #2980b9;
}

.btn.active {
  background: #27ae60;
}

.btn.active:hover {
  background: #229954;
}

.btn:disabled {
  background: #7f8c8d;
  cursor: not-allowed;
}

.btn-danger {
  background: #e74c3c;
}

.btn-danger:hover {
  background: #c0392b;
}

.btn-purple {
  background: #9b59b6;
}

.btn-purple:hover {
  background: #8e44ad;
}

.btn-teal {
  background: #16a085;
}

.btn-teal:hover {
  background: #1abc9c;
}

.toolbar-btn {
  width: auto;
  margin-bottom: 0;
  padding: 8px 16px;
}

.grid-input {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.grid-input label {
  flex: 0 0 50px;
  margin-bottom: 0;
  font-size: 13px;
}

.grid-input input[type="number"] {
  width: 80px;
  padding: 5px;
  border: 1px solid #555;
  background: #34495e;
  color: white;
  border-radius: 3px;
}

.legend {
  margin-top: 15px;
}

.legend-title {
  font-weight: bold;
  font-size: 13px;
  display: block;
  margin-bottom: 5px;
}

.legend-items {
  display: flex;
  gap: 10px;
  margin-top: 5px;
  align-items: center;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-swatch {
  width: 20px;
  height: 20px;
  border: 1px solid white;
}

.legend-label {
  font-size: 12px;
}

.checkbox-row {
  margin-top: 10px;
}

.checkbox-row label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  cursor: pointer;
}

.template-help {
  margin-top: 10px;
  font-size: 11px;
  color: #bdc3c7;
}

/* Collapsible Track Lines section */
.section-track-lines {
  margin-bottom: 0;
  padding-bottom: 20px;
}

.section-header-collapsible {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  user-select: none;
}

.section-header-collapsible:hover {
  color: #3498db;
}

.expand-icon {
  font-size: 10px;
  transition: transform 0.2s;
}

.show-more,
.show-less {
  text-align: center;
  padding: 8px;
  color: #3498db;
  cursor: pointer;
  font-size: 12px;
  background: #34495e;
  border-radius: 4px;
}

.show-more:hover,
.show-less:hover {
  background: #3e5771;
  color: #5dade2;
}

.btn-export {
  background: #27ae60;
  font-weight: bold;
}

.btn-export:hover {
  background: #2ecc71;
}

.btn-sync {
  background: #3498db;
  font-weight: bold;
}

.btn-sync:hover {
  background: #2980b9;
}

.btn-sync:disabled {
  background: #7f8c8d;
  cursor: not-allowed;
}

.sync-hint {
  margin-top: 6px;
  font-size: 11px;
  color: #95a5a6;
}

.point-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.point-list::-webkit-scrollbar {
  display: none;
}

.point-item {
  background: #34495e;
  padding: 10px;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  font-size: 11px;
  gap: 8px;
  cursor: pointer;
}

.point-item.selected {
  border: 2px solid #f39c12;
  box-shadow: 0 0 10px rgba(243, 156, 18, 0.5);
  background: #3e5771;
}

.point-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.point-header {
  display: flex;
  align-items: center;
  gap: 5px;
}

.point-label {
  font-weight: bold;
}

.point-label.selected {
  color: #f39c12;
}

.point-length {
  font-size: 10px;
  color: #95a5a6;
}

.point-coords {
  display: flex;
  gap: 5px;
  align-items: center;
}

.coord-label {
  font-size: 10px;
  width: 35px;
}

.point-coords input[type="number"] {
  width: 60px;
  padding: 3px 5px;
  border: 1px solid #555;
  background: #2c3e50;
  color: white;
  border-radius: 3px;
  font-size: 11px;
}

.point-actions {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.btn-invert {
  background: #3498db;
  color: white;
  border: none;
  padding: 3px 8px;
  cursor: pointer;
  border-radius: 3px;
  font-size: 11px;
}

.btn-delete {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 3px 8px;
  cursor: pointer;
  border-radius: 3px;
  font-size: 11px;
}

.save-section,
.load-section,
.export-section {
  margin-bottom: 15px;
}

.section-label {
  font-size: 12px;
  display: block;
  margin-bottom: 5px;
}

.save-input {
  width: 100%;
  margin-top: 5px;
  margin-bottom: 5px;
  padding: 8px;
  background: #34495e;
  color: white;
  border: 1px solid #555;
  border-radius: 3px;
  font-size: 12px;
}

.current-config {
  margin-top: 5px;
  font-size: 11px;
  color: #3498db;
}

.config-name {
  font-weight: bold;
}

.config-select {
  width: 100%;
  margin-top: 5px;
  padding: 5px;
  background: #34495e;
  color: white;
  border: 1px solid #555;
  border-radius: 3px;
}

.load-buttons,
.export-buttons {
  display: flex;
  gap: 5px;
  margin-top: 5px;
}

.load-buttons .btn,
.export-buttons .btn {
  flex: 1;
}

.export-hint {
  margin-top: 5px;
  font-size: 10px;
  color: #95a5a6;
}

.main-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.toolbar {
  background: #34495e;
  color: white;
  padding: 10px 20px;
  display: flex;
  gap: 15px;
  align-items: center;
}

.toolbar-spacer {
  flex: 1;
}

.mode-indicator {
  display: inline-block;
  padding: 3px 8px;
  background: #27ae60;
  border-radius: 3px;
  font-size: 11px;
  margin-left: 10px;
}

.mouse-coords {
  font-family: 'Courier New', monospace;
  font-size: 12px;
}

.canvas-container {
  flex: 1;
  overflow-x: auto;
  overflow-y: hidden;
  background: #ecf0f1;
  position: relative;
}

.canvas-container::-webkit-scrollbar {
  height: 12px;
}

.canvas-container::-webkit-scrollbar-track {
  background: #bdc3c7;
}

.canvas-container::-webkit-scrollbar-thumb {
  background: #7f8c8d;
  border-radius: 6px;
}

.canvas-container::-webkit-scrollbar-thumb:hover {
  background: #5d6d7e;
}

canvas {
  display: block;
  cursor: crosshair;
}

.status-bar {
  padding: 5px 20px;
  background: #2c3e50;
  color: white;
  font-size: 12px;
  border-top: 1px solid #34495e;
}

/* Modal */
.modal {
  position: fixed;
  z-index: 1000;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-content {
  background-color: #2c3e50;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
  max-width: 400px;
  width: 90%;
}

.modal-title {
  color: #e74c3c;
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 15px;
}

.modal-message {
  color: white;
  font-size: 14px;
  margin-bottom: 25px;
  line-height: 1.5;
  white-space: pre-wrap;
}

.modal-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.modal-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  font-weight: bold;
}

.modal-btn-confirm {
  background: #e74c3c;
  color: white;
}

.modal-btn-confirm:hover {
  background: #c0392b;
}

.modal-btn-cancel {
  background: #7f8c8d;
  color: white;
}

.modal-btn-cancel:hover {
  background: #5d6d7e;
}
</style>
