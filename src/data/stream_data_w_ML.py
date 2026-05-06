"""
Streaming de données en temps réel depuis Binance WebSocket.
"""
import json
import logging
import threading
import time
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any
from pymongo.database import Database
import websocket

try:
    from .config import SETTINGS
except ImportError:
    from config import SETTINGS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("STREAM_DATA")


class BinanceStreamClient:

    def __init__(self, symbols: List[str], db: Optional[Database] = None,
                 callback: Optional[Callable] = None):
        self.symbols = [s.lower() for s in symbols]
        self.db = db
        self.callback = callback
        self.ws = None
        self.ws_url = self._build_url()
        self.running = False
        self.thread = None
        self.reconnect_delay = 5
        self.max_reconnect_attempts = 10

    def _build_url(self) -> str:
        base_url = SETTINGS["URL_STREAM"]
        """ajout de bid et ask pour avoir les prix executable"""
        streams = "/".join([f"{symbol}@trade" for symbol in self.symbols
                            ] + [f"{symbol}@bookTicker" for symbol in self.symbols])
        return f"{base_url}/{streams}"

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            event_type = data.get("e")

            if event_type == "trade":
                parsed_data = {
                    "type":           "trade",
                    "symbol":         data.get("s"),
                    "price":          float(data.get("p", 0)),
                    "quantity":       float(data.get("q", 0)),
                    "timestamp":      datetime.fromtimestamp(data.get("T", 0) / 1000),
                    "trade_id":       data.get("t"),
                    "is_buyer_maker": data.get("m", False),
                }

            elif event_type is None:
                parsed_data = {
                    "type":      "bookTicker",
                    "symbol":    data.get("s"),
                    "bid_price": float(data.get("b", 0)),
                    "bid_qty":   float(data.get("B", 0)),
                    "ask_price": float(data.get("a", 0)),
                    "ask_qty":   float(data.get("A", 0)),
                    "timestamp": datetime.utcnow(),
                }

            else:
                logger.warning(f"Message de type inconnu : {data}")
                return

            logger.debug(f"Received {parsed_data['type']}: {parsed_data['symbol']}")

            if self.db is not None:
                self._store_trade(parsed_data)

            if self.callback is not None:
                self.callback(parsed_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"WebSocket closed: {close_status_code} - {close_msg}")
        if self.running:
            logger.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)
            if self.running:
                self._connect()

    def _on_open(self, ws):
        logger.info(f"WebSocket connected to {self.ws_url}")
        logger.info(f"Streaming data for symbols: {', '.join(self.symbols)}")

    def _store_trade(self, trade_data: Dict[str, Any]):
        try:
            collection_name = SETTINGS["MONGO_COLLECTION_STREAMING"]
            collection = self.db[collection_name]
            collection.insert_one(trade_data)
        except Exception as e:
            logger.error(f"Error storing trade in MongoDB: {e}")

    def _connect(self):
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            self.ws.run_forever()
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            if self.running:
                time.sleep(self.reconnect_delay)
                self._connect()

    def start(self):
        if self.running:
            logger.warning("Stream is already running")
            return
        self.running = True
        self.thread = threading.Thread(target=self._connect, daemon=True)
        self.thread.start()
        logger.info("Stream started in background thread")

    def stop(self):
        if not self.running:
            logger.warning("Stream is not running")
            return
        self.running = False
        if self.ws:
            self.ws.close()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Stream stopped")

    def stream_for_duration(self, duration_seconds: int):
        logger.info(f"Starting stream for {duration_seconds} seconds...")
        self.start()
        try:
            time.sleep(duration_seconds)
        except KeyboardInterrupt:
            logger.info("Stream interrupted by user")
        finally:
            self.stop()


def stream_trades(symbols: List[str], duration_seconds: Optional[int] = None,
                  db: Optional[Database] = None,
                  callback: Optional[Callable] = None) -> BinanceStreamClient:
    """
    Fonction helper pour streamer les trades.

    Args:
        symbols: Liste des symboles à streamer
        duration_seconds: Durée du stream (None = infini)
        db: Base de données MongoDB (optionnel)
        callback: Fonction callback pour chaque trade (optionnel)

    Returns:
        BinanceStreamClient: Instance du client
    """
    client = BinanceStreamClient(symbols=symbols, db=db, callback=callback)
    if duration_seconds:
        client.stream_for_duration(duration_seconds)
    else:
        client.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping stream...")
            client.stop()
    return client


if __name__ == "__main__":
    def print_trade(data):
        if data["type"] == "trade":
            print(f"[TRADE] {data['symbol']}: ${data['price']:.2f}")
        elif data["type"] == "bookTicker":
            print(f"[BOOK]  {data['symbol']}: bid=${data['bid_price']:.2f} ask=${data['ask_price']:.2f}")

    stream_trades(['BTCUSDT'], duration_seconds=30, callback=print_trade)