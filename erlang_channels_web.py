from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)

class ErlangCalculator:
    """Calcul du nombre de canaux selon la formule d'Erlang B"""
    
    @staticmethod
    def erlang_b(N, A):
        """
        Calcule la probabilité de perte Erlang B
        N: nombre de canaux
        A: trafic en Erlangs
        """
        if N == 0:
            return 1.0 if A > 0 else 0.0
        
        # Éviter les débordements de calcul
        try:
            numerator = (A ** N) / math.factorial(N)
            denominator = sum((A ** k) / math.factorial(k) for k in range(N + 1))
            return numerator / denominator
        except (OverflowError, ValueError):
            return 1.0
    
    @staticmethod
    def erlang_b_inverse(A, Pr, max_channels=1000):
        """
        Calcule le nombre de canaux nécessaires
        A: trafic en Erlangs
        Pr: probabilité de perte acceptée (Grade of Service)
        max_channels: nombre maximum de canaux à tester
        """
        if A <= 0:
            return 0
        if Pr >= 1.0:
            return 1
        
        for N in range(1, max_channels + 1):
            if ErlangCalculator.erlang_b(N, A) <= Pr:
                return N
        
        return max_channels

    @staticmethod
    def erlang_a_from_pr(N, Pr, tol=1e-9, max_iter=100, max_A=1e6):
        """
        Calcule le trafic A (Erlangs) tel que la probabilité de perte pour N canaux
        soit égale à Pr. Résout erlang_b(N, A) = Pr par recherche binaire.
        N: nombre de canaux (int)
        Pr: probabilité de perte cible (0 <= Pr < 1)
        """
        if N <= 0:
            raise ValueError("N doit être strictement positif")
        if Pr <= 0:
            return 0.0
        if Pr >= 1.0:
            return float('inf')

        # Chercher une borne supérieure suffisante
        low = 0.0
        high = 1.0
        try:
            while ErlangCalculator.erlang_b(N, high) < Pr and high < max_A:
                high *= 2.0
        except Exception:
            return max_A

        if ErlangCalculator.erlang_b(N, high) < Pr:
            return max_A

        # Recherche binaire
        for _ in range(max_iter):
            mid = (low + high) / 2.0
            val = ErlangCalculator.erlang_b(N, mid)
            if abs(val - Pr) <= tol:
                return mid
            if val < Pr:
                low = mid
            else:
                high = mid

        return (low + high) / 2.0


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/calculate_channels', methods=['POST'])
def calculate_channels():
    try:
        data = request.json
        A = float(data.get('A'))
        Pr = float(data.get('Pr'))
        
        if A <= 0:
            return jsonify({'error': 'Le trafic A doit être positif'}), 400
        if Pr <= 0 or Pr >= 1:
            return jsonify({'error': 'Pr doit être entre 0 et 1'}), 400
        
        N = ErlangCalculator.erlang_b_inverse(A, Pr)
        return jsonify({'result': f'{N} canaux'})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/calculate_loss_prob', methods=['POST'])
def calculate_loss_prob():
    try:
        data = request.json
        A = float(data.get('A'))
        N = int(data.get('N'))
        
        if A <= 0:
            return jsonify({'error': 'Le trafic A doit être positif'}), 400
        if N <= 0:
            return jsonify({'error': 'Le nombre de canaux doit être positif'}), 400
        
        Pr = ErlangCalculator.erlang_b(N, A)
        Pr_percent = Pr * 100
        
        return jsonify({
            'Pr': f'{Pr:.6f}',
            'Pr_percent': f'{Pr_percent:.4f}%'
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/calculate_traffic_a', methods=['POST'])
def calculate_traffic_a():
    try:
        data = request.json
        N = int(data.get('N'))
        Pr = float(data.get('Pr'))
        
        if N <= 0:
            return jsonify({'error': 'Le nombre de canaux doit être positif'}), 400
        if Pr < 0 or Pr >= 1:
            return jsonify({'error': 'Pr doit être dans [0, 1)'}), 400
        
        A = ErlangCalculator.erlang_a_from_pr(N, Pr)
        
        if A == float('inf'):
            result = 'Infini (Pr proche de 1)'
        else:
            result = f'{A:.6f} Erlangs'
        
        return jsonify({'result': result})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)
