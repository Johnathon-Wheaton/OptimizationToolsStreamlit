# Instructions

This app helps you solve optimization problems using AI agents. When you describe your problem, an AI consultant will ask questions to understand all the details. After gathering information, a team of AI agents will formulate and solve your optimization model.

## How to Use

1. Enter your OpenAI API key and select a model in the sidebar
2. Describe your optimization problem in plain language 
3. Answer the consultant's questions about your problem
4. Wait while the AI team solves your problem
5. Download the Excel file containing the solution

## Tips for Best Results

- Provide as much detail as possible in your initial description
- Use specific numbers and units
- Specify if you want to maximize or minimize something
- Mention any constraints or requirements
- Default solver time limit is 10 minutes
- Default optimality gap is 0.01 (1%)

# Example Problems

## 1. Multi-Period Production Planning

"I need help planning production for our factory that makes 3 types of products (A, B, C) over the next 4 months. Each product requires different amounts of our 2 raw materials:
- Product A: 2 units of material 1, 3 units of material 2
- Product B: 4 units of material 1, 1 unit of material 2  
- Product C: 1 unit of material 1, 2 units of material 2

We can store up to 1000 units of each product between months. Storage costs $2 per unit per month.

Monthly production capacity is 800 hours. Production times are:
- Product A: 2 hours
- Product B: 3 hours
- Product C: 1.5 hours

Monthly demand for each product is:
Month 1: A=100, B=150, C=200
Month 2: A=120, B=130, C=180
Month 3: A=140, B=140, C=160
Month 4: A=130, B=160, C=150

We want to minimize total production and storage costs. Production costs per unit are:
- Product A: $50
- Product B: $80
- Product C: $40"

## 2. Vehicle Routing with Time Windows 

"I need to optimize delivery routes for our 3 trucks. Each truck has 8 hours of drive time and can carry up to 2000 kg.

We need to deliver to 12 customers. Each customer has:
- A specific delivery window (e.g. Customer 1 must receive delivery between 9am-11am)
- A delivery amount in kg
- Service time of 15 minutes per delivery
- Location coordinates (x,y)

Truck speed is 40 km/hr. Distance is Euclidean.

Customer data:
1. (10,15), 300kg, 9am-11am
2. (15,10), 400kg, 8am-10am
3. (8,8), 250kg, 10am-12pm
4. (12,12), 350kg, 11am-1pm
5. (5,15), 600kg, 9am-12pm
6. (15,5), 450kg, 8am-11am
7. (9,12), 500kg, 10am-2pm
8. (11,8), 300kg, 9am-12pm
9. (7,7), 400kg, 11am-2pm
10. (14,14), 550kg, 10am-1pm
11. (6,10), 280kg, 8am-10am
12. (13,7), 320kg, 9am-11am

Minimize total distance traveled while meeting all time windows."

## 3. Staff Scheduling with Multiple Skills

"I need to create a 4-week staff schedule for our call center. We have 20 employees with different skills and availability.

Skills needed:
- Technical Support (Tech)
- Customer Service (CS)
- Billing Support (Bill)

Each shift needs minimum staffing:
Weekdays:
- Morning (8am-4pm): 3 Tech, 4 CS, 2 Bill
- Evening (4pm-12am): 2 Tech, 3 CS, 1 Bill

Weekends:
- Morning: 2 Tech, 2 CS, 1 Bill
- Evening: 1 Tech, 2 CS, 1 Bill

Employee skills (they can work any position they're trained in):
- 5 employees: All skills
- 8 employees: Tech + CS
- 4 employees: CS + Bill
- 3 employees: CS only

Labor rules:
- 40 hours/week maximum
- At least 2 days off per week
- No more than 5 consecutive days
- 12 hours minimum between shifts
- Maximum 50% evening shifts per employee

Each employee provided preferred days off. We want to minimize dissatisfaction by maximizing preferred days off granted while meeting all staffing requirements."