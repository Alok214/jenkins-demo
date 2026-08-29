"""Flask demo app - mirrors Spring Boot app in sosuv-workflow-api."""
from decimal import Decimal, InvalidOperation

from flask import Flask, jsonify, request

from app.calculator import add, divide

app = Flask(__name__)


def _parse_decimal(value, name):
    if value is None or value == "":
        raise ValueError(f"{name} is required")

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be a valid number") from exc

    if not number.is_finite():
        raise ValueError(f"{name} must be a finite number")

    return number


@app.route("/")
def home():
    return jsonify({
        "message": "Hello from jenkins-demo Python app!",
        "status": "running",
        "version": "1.0.0"
    })


@app.route("/health")
def health():
    return jsonify({"status": "UP"})


@app.route("/calc/add")
def calc_add():
    try:
        a = _parse_decimal(request.args.get("a", 0), "a")
        b = _parse_decimal(request.args.get("b", 0), "b")
        result = add(float(a), float(b))
        return jsonify({"operation": "add", "a": float(a), "b": float(b), "result": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/calc/divide")
def calc_divide():
    try:
        a = _parse_decimal(request.args.get("a", 0), "a")
        b = _parse_decimal(request.args.get("b", 1), "b")
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = divide(float(a), float(b))
        return jsonify({"operation": "divide", "a": float(a), "b": float(b), "result": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
