# Jyora Phonix 📱

**A smartphone discovery and comparison platform focused on specifications, processor information, and evidence-based performance insights.**

## Overview

Jyora Phonix helps users explore smartphones, compare specifications, and discover devices based on their budget and priorities.

Instead of relying only on specification numbers, the platform also supports sourced gaming-performance records to help users understand real-world performance.

## Features

- **Smartphone Discovery:** Browse available devices and their specifications.
- **Budget-Based Recommendations:** Find devices within a selected budget.
- **Priority-Based Recommendations:** Explore devices based on balanced usage, gaming performance, battery, camera, and display.
- **Phone Comparison:** Compare smartphone specifications.
- **Processor Lab:** Explore processor and GPU information.
- **Gaming Performance Evidence:** Display recorded FPS results with test details and source links when available.
- **Admin Management:** Manage phone data, processor information, and performance records through Django Admin.

## Technology Stack

- **Backend:** Python, Django
- **Database:** MySQL or the database configured for the project
- **Frontend:** HTML, CSS, Django Templates
- **Data Management:** CSV import and Django ORM

## Getting Started

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd jyora_phonix
```

Replace the repository URL and directory name with the actual values for your GitHub project.

### 2. Install dependencies

```bash
py -m pip install -r requirements.txt
```

### 3. Configure environment variables

Set up the database and other required settings for your local environment. Do not commit passwords, secret keys, or `.env` files containing credentials.

### 4. Apply database migrations

```bash
py manage.py migrate
```

### 5. Start the development server

```bash
py manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

## Performance Data Disclaimer

Gaming FPS figures are specific to the cited test setup, game, settings, and device configuration. They should not be treated as universal benchmarks.

Prices imported from the dataset are reference or launch prices, not verified current retail prices.

## Future Improvements

- Expand and validate the smartphone dataset.
- Add more independently sourced gaming benchmarks.
- Improve processor comparisons using consistent benchmark methodologies.
- Add current retail pricing from reliable sources.

## Project Status

Developed as a student project exploring smartphone discovery, data management, recommendation logic, and performance-data presentation.
