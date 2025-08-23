import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

// Placeholder components - will be implemented in separate files
const SpendingForm = ({ categories, spending, setSpending }) => (
  <div>
    <h2>Enter Your Monthly Spending</h2>
    {categories.map(category => (
      <div key={category.key}>
        <label>{category.display_name}</label>
        <input
          type="number"
          value={spending[category.key] || ''}
          onChange={e => setSpending({ ...spending, [category.key]: parseInt(e.target.value, 10) || 0 })}
        />
      </div>
    ))}
  </div>
);

const CardSelector = ({ cards, selectedCards, setSelectedCards }) => {
  const handleCheckboxChange = (cardName) => {
    const newSelectedCards = selectedCards.includes(cardName)
      ? selectedCards.filter(name => name !== cardName)
      : [...selectedCards, cardName];
    setSelectedCards(newSelectedCards);
  };

  return (
    <div>
      <h2>Select Your Credit Cards</h2>
      {cards.map(card => (
        <div key={card.name}>
          <input
            type="checkbox"
            id={card.name}
            checked={selectedCards.includes(card.name)}
            onChange={() => handleCheckboxChange(card.name)}
          />
          <label htmlFor={card.name}>{card.name}</label>
        </div>
      ))}
    </div>
  );
};

const ResultsDisplay = ({ results }) => {
  if (!results) {
    return null;
  }

  return (
    <div>
      <h2>Optimization Results</h2>
      <h3>Total Annual Savings: ${results.total_savings.toFixed(2)}</h3>
      {results.chosen_plan && <h4>Recommended Plan: {results.chosen_plan}</h4>}
      {/* Basic table for results */}
      <table>
        <thead>
          <tr>
            <th>Category</th>
            <th>Card</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {results.results_df.map((row, i) => (
            <tr key={i}>
              <td>{row.Category}</td>
              <td>{row.Card}</td>
              <td>${row.Amount.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};


function App() {
  const [cards, setCards] = useState([]);
  const [categories, setCategories] = useState([]);
  const [spending, setSpending] = useState({});
  const [selectedCards, setSelectedCards] = useState([]);
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch initial data for cards and categories
    const fetchData = async () => {
      try {
        const [cardsRes, categoriesRes] = await Promise.all([
          axios.get('http://localhost:8000/cards'),
          axios.get('http://localhost:8000/categories')
        ]);
        setCards(cardsRes.data);
        setCategories(categoriesRes.data);
        // Initially select all cards
        setSelectedCards(cardsRes.data.map(c => c.name));
      } catch (err) {
        setError('Failed to fetch initial data. Make sure the backend server is running.');
        console.error(err);
      }
    };
    fetchData();
  }, []);

  const handleOptimize = async () => {
    setIsLoading(true);
    setError(null);
    setResults(null);

    const payload = {
      monthly_spending: spending,
      selected_card_names: selectedCards,
    };

    try {
      const response = await axios.post('http://localhost:8000/optimize', payload);
      if (response.data.error) {
        setError(response.data.error);
      } else {
        setResults(response.data);
      }
    } catch (err) {
      setError('An error occurred during optimization.');
      console.error(err);
    }
    setIsLoading(false);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Credit Card Optimizer</h1>
      </header>
      <main>
        <div className="container">
          <div className="sidebar">
            <SpendingForm categories={categories} spending={spending} setSpending={setSpending} />
            <CardSelector cards={cards} selectedCards={selectedCards} setSelectedCards={setSelectedCards} />
            <button onClick={handleOptimize} disabled={isLoading}>
              {isLoading ? 'Optimizing...' : 'Optimize'}
            </button>
          </div>
          <div className="content">
            {error && <p className="error">{error}</p>}
            {results && <ResultsDisplay results={results} />}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
