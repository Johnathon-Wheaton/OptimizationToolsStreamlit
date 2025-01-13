# Supply Chain Network Optimization Tools

A suite of optimization tools for supply chain network design and logistics, built with Streamlit. This application provides various optimization algorithms to solve common supply chain problems including facility location and vehicle routing.

## Features

### 1. Facility Location Optimization (MILP)
- Optimize facility locations from a set of candidate sites
- Consider fixed costs and transportation costs
- Account for facility capacities and customer demands
- Visualize results on an interactive map
- Uses PuLP solver for Mixed Integer Linear Programming

### 2. Facility Location Optimization (PSO)
- Find optimal facility locations without predefined candidates
- Uses Particle Swarm Optimization for continuous location selection
- Consider facility capacities and customer demands
- Balances fixed costs and transportation costs
- Visualize optimization progress and final results

### 3. Vehicle Routing Optimization
- Optimize delivery routes for multiple vehicles
- Optional capacity constraints
- Optional time window constraints
- Service time consideration at each stop
- Uses Google OR-Tools for routing optimization
- Interactive route visualization

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/supply-chain-optimization.git
cd supply-chain-optimization
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```
3. Install required packages:
```bash
pip install -r requirements.txt
```
## Dependencies

streamlit
pandas
numpy
pulp
ortools
pydeck

## Usage
1. Run the Streamlit app:
```bash
streamlit run app.py
```
2. Navigate to the tool you want to use from the sidebar
3. Download the appropriate template Excel file
4. Fill in your data following the template format
5. Upload your completed template
6. Adjust optimization parameters as needed
7. Run the optimization
8. View and analyze results

## Usage
### Facility Location MILP

facilities: Candidate facility locations with fixed costs and capacities
customers: Customer locations and demands
distances: Distance matrix between facilities and customers

### Facility Location PSO

customers: Customer locations and demands

### Vehicle Routing

locations: All locations including depot and delivery points

Time windows (optional)
Service times
Demands

## Directory Structure
```bash
supply-chain-optimization/
├── app.py
├── requirements.txt
├── README.md
├── pages/
│   ├── 01_facility_milp.py
│   ├── 02_facility_pso.py
│   └── 03_vrp.py
├── src/
│   ├── components/
│   │   ├── file_handlers.py
│   │   └── parameter_controls.py
│   ├── optimization/
│   │   ├── facility_milp.py
│   │   ├── facility_pso.py
│   │   └── vrp.py
│   └── utils/
│       ├── mapping.py
│       ├── pso_mapping.py
│       └── vrp_mapping.py
└── templates/
    ├── facility_milp.xlsx
    ├── facility_pso.xlsx
    └── vrp.xlsx
```
## Contributing
Fork the repository
Create a new branch (git checkout -b feature/improvement)
Make your changes
Commit your changes (git commit -am 'Add new feature')
Push to the branch (git push origin feature/improvement)
Create a Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
Streamlit for the web framework
PuLP for MILP optimization
Google OR-Tools for vehicle routing optimization