const PIECE_TO_UNICODE = {
  p: '♟',
  r: '♜',
  n: '♞',
  b: '♝',
  q: '♛',
  k: '♚',
  P: '♙',
  R: '♖',
  N: '♘',
  B: '♗',
  Q: '♕',
  K: '♔',
};

const boardElement = document.getElementById('board');
const overlayElement = document.getElementById('board-overlay');
const statusElement = document.getElementById('status');
const moveListElement = document.getElementById('move-list');
const newGameButton = document.getElementById('new-game');

const squareElements = new Map();
let currentGame = null;
let selectedSquare = null;
let legalMoves = {};
let boardPositions = {};

function createBoard() {
  const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  boardElement.innerHTML = '';
  squareElements.clear();

  for (let rank = 8; rank >= 1; rank -= 1) {
    for (let fileIndex = 0; fileIndex < 8; fileIndex += 1) {
      const file = files[fileIndex];
      const squareName = `${file}${rank}`;
      const squareDiv = document.createElement('div');
      const isLight = (fileIndex + rank) % 2 === 0;
      squareDiv.classList.add('square', isLight ? 'light' : 'dark');
      squareDiv.dataset.square = squareName;
      squareDiv.addEventListener('click', () => onSquareClick(squareName));
      boardElement.appendChild(squareDiv);
      squareElements.set(squareName, squareDiv);
    }
  }
}

function parseFenBoard(fen) {
  const [piecePlacement] = fen.split(' ');
  const ranks = piecePlacement.split('/');
  const squares = {};
  let rankIndex = 8;

  ranks.forEach((rankString) => {
    let fileIndex = 0;
    rankString.split('').forEach((char) => {
      if (Number.isInteger(Number.parseInt(char, 10))) {
        fileIndex += Number.parseInt(char, 10);
      } else {
        const squareName = `${String.fromCharCode('a'.charCodeAt(0) + fileIndex)}${rankIndex}`;
        squares[squareName] = char;
        fileIndex += 1;
      }
    });
    rankIndex -= 1;
  });
  return squares;
}

function renderBoard(fen) {
  boardPositions = parseFenBoard(fen);
  for (const [square, element] of squareElements.entries()) {
    const piece = boardPositions[square];
    element.textContent = piece ? PIECE_TO_UNICODE[piece] : '';
    element.dataset.piece = piece || '';
    element.classList.remove('selected', 'destination', 'white-piece', 'black-piece');
    if (piece) {
      const isWhite = piece === piece.toUpperCase();
      element.classList.add(isWhite ? 'white-piece' : 'black-piece');
    }
  }
  selectedSquare = null;
}

function highlightMoves(square) {
  clearHighlights();
  if (!legalMoves[square]) {
    return;
  }
  const squareElement = squareElements.get(square);
  if (squareElement) {
    squareElement.classList.add('selected');
  }
  legalMoves[square].forEach((move) => {
    const target = squareElements.get(move.to);
    if (target) {
      target.classList.add('destination');
    }
  });
}

function clearHighlights() {
  for (const element of squareElements.values()) {
    element.classList.remove('selected', 'destination');
  }
}

function onSquareClick(square) {
  if (!currentGame) {
    return;
  }
  const piece = boardPositions[square];
  const isWhitePiece = piece && piece === piece.toUpperCase();

  if (selectedSquare && square === selectedSquare) {
    selectedSquare = null;
    clearHighlights();
    return;
  }

  if (selectedSquare) {
    const moves = legalMoves[selectedSquare] || [];
    const chosenMove = moves.find((move) => move.to === square);
    if (chosenMove) {
      sendMove(chosenMove);
      return;
    }
    if (isWhitePiece) {
      selectedSquare = square;
      highlightMoves(square);
    } else {
      selectedSquare = null;
      clearHighlights();
    }
    return;
  }

  if (isWhitePiece && (legalMoves[square] || []).length > 0) {
    selectedSquare = square;
    highlightMoves(square);
  }
}

function buildMovePayload(move) {
  const payload = {
    game_id: currentGame.game_id,
    source: move.source,
    target: move.to,
  };

  if (move.uci) {
    payload.uci = move.uci;
  }

  if (move.promotion) {
    payload.promotion = move.promotion;
  }

  return payload;
}

async function sendMove(move) {
  if (!currentGame) {
    return;
  }
  showOverlay('Engine thinking...');
  try {
    const response = await fetch('/api/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(buildMovePayload(move)),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Move rejected');
    }
    const state = await response.json();
    updateState(state);
  } catch (error) {
    console.error(error);
    statusElement.textContent = `Error: ${error.message}`;
  } finally {
    if (currentGame && (currentGame.status === 'ongoing' || currentGame.status === 'check')) {
      hideOverlay();
    }
  }
}

function updateState(state) {
  currentGame = state;
  legalMoves = state.legal_moves || {};
  renderBoard(state.fen);
  updateStatus(state.status, state.turn);
  updateMoveList(state.history);
  if (state.status !== 'ongoing' && state.status !== 'check') {
    showOverlay(state.status.toUpperCase());
  } else {
    hideOverlay();
  }
}

function updateStatus(status, turn) {
  const turnText = turn === 'white' ? "Your move" : "TalBot to move";
  statusElement.textContent = status === 'check' ? `${turnText} – check!` : `${turnText} – ${status}`;
}

function updateMoveList(history) {
  moveListElement.innerHTML = '';
  history.forEach((record) => {
    const item = document.createElement('li');
    const blackPart = record.black ? ` ... ${record.black}` : '';
    item.textContent = `${record.move_number}. ${record.white}${blackPart}`;
    moveListElement.appendChild(item);
  });
  moveListElement.scrollTop = moveListElement.scrollHeight;
}

function showOverlay(message) {
  overlayElement.textContent = message;
  overlayElement.classList.add('visible');
}

function hideOverlay() {
  overlayElement.classList.remove('visible');
}

async function startNewGame() {
  showOverlay('Loading...');
  try {
    const response = await fetch('/api/new', { method: 'POST' });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Unable to start game');
    }
    const state = await response.json();
    updateState(state);
  } catch (error) {
    statusElement.textContent = `Error: ${error.message}`;
  } finally {
    hideOverlay();
  }
}

function initialize() {
  createBoard();
  newGameButton.addEventListener('click', () => startNewGame());
  startNewGame();
}

window.addEventListener('DOMContentLoaded', initialize);
