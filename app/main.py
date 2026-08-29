"""Flask demo app - mirrors Spring Boot app in sosuv-workflow-api."""
from flask import Flask, jsonify, request
from app.calculator import add, subtract, multiply, divide, power

app = Flask(__name__)

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
        a = float(request.args.get("a", 0))
        b = float(request.args.get("b", 0))
        return jsonify({"operation": "add", "a": a, "b": b, "result": add(a, b)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/calc/divide")
def calc_divide():
    try:
        a = float(request.args.get("a", 0))
        b = float(request.args.get("b", 1))
        return jsonify({"operation": "divide", "a": a, "b": b, "result": divide(a, b)})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
