import yfinance as yf
import json

# Ver el archivo .json por si hay algo mas de valor

def get_news(ticker: str, limit: int = 10):
  data = yf.Ticker(ticker).get_news(count=limit)
  
  '''
  Get the 10 most recent news of a given ticker
  '''
  
  # with open("aapl_news.json", "w", encoding="utf-8") as f:
  #   json.dump(data, f, indent=2, ensure_ascii=False)
    
  results = []

  for n in data:
    content = n.get("content", {})
    results.append({
      "title": content.get("title"),
      "link": content.get("canonicalUrl", {}).get("url"),
      "publisher": content.get("provider", {}).get("displayName"),
      "time": content.get("pubDate"),
      "summary": content.get("summary")
    })

  return results

if __name__ == "__main__":
  news = get_news("AAPL")
  for n in news:
    print(f"{n['title']} ({n['publisher']})")
    print(f"{n['link']} - {n['time']}")
    print(f"SUMMARY: {n['summary']}")
    print('---')
