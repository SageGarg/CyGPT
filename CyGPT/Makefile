.PHONY: setup ingest run clean-cache clean-index

setup:
	pip install -r requirements.txt

ingest:
	python ingest.py

ingest-more:
	python ingest.py --max-urls 500

run:
	streamlit run app.py

clean-cache:
	rm -rf data/cache/*
	@echo "Disk cache cleared. Next ingest will re-scrape all pages."

clean-index:
	rm -f data/index/*.index data/index/*.pkl
	@echo "Index cleared. Run 'make ingest' to rebuild."

clean: clean-cache clean-index
