# AI Prompt History
## SCD Type 2 Customer Data Pipeline

The following prompts document the AI-assisted development process, from understanding the assignment to testing and preparing the final project.

1. I have been given a data engineering assignment on SCD Type 2. Can you help me understand what needs to be built and how customer history is maintained when their details change?

2. I am planning to use Python and SQLite for this project. Is that enough? Suggest a simple approach that I can implement without using too many libraries or complicated tools.

3. Before writing the code, help me decide what database tables I need. I want to store customer history, incoming events, invalid records and pipeline execution details separately.

4. Help me create a proper folder structure for this project. Keep separate folders for Python code, tests, sample data and documentation. Also include requirements.txt and .gitignore.

5. Let's start with the main Python code. Write a function to read customer data from a CSV file containing customer_id, event_id, effective_at, name, email and city. Make sure it checks the required columns.

6. How should I handle the effective_at column? Help me convert timezone-aware timestamps into UTC and reject timestamps that don't contain timezone information.

7. Add basic validations to the CSV processing. Check for missing values and invalid email addresses. Store invalid rows separately along with the reason they failed instead of simply ignoring them.

8. Now help me implement the actual SCD Type 2 logic. Whenever a customer's name, email or city changes, close the old record and insert a new version. If nothing changes, don't create another record.

9. Can we use hashing to identify changes in customer details instead of comparing every column manually? Generate a consistent hash using name, email and city and use it for change detection.

10. Connect the pipeline to SQLite and store the incoming events and customer history. Also create separate tables for invalid records and pipeline runs. Make sure database changes are handled safely if an error occurs.

11. What happens if the same event comes more than once? Use event_id to identify duplicates. Skip exact duplicates, but reject an event if the same ID is reused with different data.

12. I want to make sure running the same CSV file multiple times doesn't create duplicate customer records. Update the pipeline to support this and show me how to verify it.

13. Events might not always arrive in the correct order. For example, an older customer update may arrive after a newer one. How can I handle this so that customer history is still arranged according to effective_at?

14. What if two events for the same customer have exactly the same effective timestamp? Use event_id to decide which event takes precedence, with the lexicographically greater ID winning. Both events should still be preserved in the source event table.

15. Can you review the SCD Type 2 logic and check whether each customer has exactly one current record? Also make sure historical records have valid date ranges and don't contain overlapping or unnecessary versions.

16. Create a small sample CSV file to test the pipeline. Include multiple customers, multiple updates for the same customer, a late-arriving event, a duplicate event, an invalid email and a row with a missing value.

17. The sample file is too small for testing. Create a separate Python script that generates synthetic customer events using a fixed random seed. I also need to generate 100,000 records for benchmarking.

18. I want to test the pipeline properly before completing it. Suggest test cases for duplicate events, invalid data, late events, same timestamps, repeated execution and customer history. Use Python's built-in unittest framework.

19. Now create the test file using these test cases. Use temporary SQLite databases so that every test runs independently and doesn't affect the actual project database.

20. I ran the tests and some of them failed. Help me understand the errors from the terminal output and fix the issues in the code. Make sure the changes don't break the tests that are already passing.

21. Now that the basic pipeline is working, I want to test it with 100,000 customer events. Generate the data and run the existing pipeline against it without changing the main processing logic.

22. I ran the benchmark more than once and noticed that the pipeline sometimes reports zero newly inserted records. Help me understand whether this is expected because of duplicate detection. Also show me how to check the actual number of events stored in SQLite.

23. I want a separate Python file to verify whether the processed data is correct. Check for duplicate dimension records, invalid date ranges, customers without exactly one current record and mismatches in current flags.

24. Modify the reconciliation script to save its results as a JSON file. Include the total source event count, dimension record count, individual validation results and an overall status showing whether all checks passed.

25. Help me document all the database tables and their columns. Explain what each column means and how it is used in the pipeline. Save this as docs/data_dictionary.md.

26. Create a document explaining the main decisions in this project, such as using SQLite, record hashing, duplicate handling and late-arriving events. Also mention the limitations of this approach. Save it as docs/design_tradeoffs.md.

27. Help me prepare a README for GitHub. Include the project objective, technologies used, folder structure, setup instructions, commands to run the pipeline, how to execute tests and how to generate the reconciliation report. Make sure everything matches the actual code.

28. Now review my complete project structure and implementation. Check whether all files are present, tests are passing, database files are excluded from Git and the documentation matches the code. Point out anything important I might have missed.

29. I am ready to submit the project. Help me check which files should be committed and which should be ignored. Give me the Git commands to stage the required files, check for errors, commit the changes and push the project to my GitHub repository.
