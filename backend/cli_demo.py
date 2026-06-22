#!/usr/bin/env python3
"""
Cognitive Database Agent - CLI Demo
===================================
Interactive command-line interface for testing the agent.

Usage:
    python backend/cli_demo.py

Features:
- Interactive chat with the agent
- Role switching (Admin, Manager, Viewer)
- Display of agent's thought process
- Color-coded output
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.agent.cognitive_agent import create_agent
from backend.app.db.connection import test_connection
from backend.app.agent.rag_retriever import get_knowledge_stats

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print a colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_info(text):
    """Print info message."""
    print(f"{Colors.OKCYAN}{text}{Colors.ENDC}")


def print_success(text):
    """Print success message."""
    print(f"{Colors.OKGREEN}{text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.WARNING}{text}{Colors.ENDC}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.FAIL}{text}{Colors.ENDC}")


def select_role():
    """
    Interactive role selection.

    Returns:
        Tuple of (role, region)
    """
    print_header("Select Your Role")

    print("Available roles:")
    print(f"  {Colors.BOLD}1. Admin{Colors.ENDC} - Full access to all data")
    print(f"  {Colors.BOLD}2. Manager{Colors.ENDC} - Regional access only")
    print(f"  {Colors.BOLD}3. Viewer{Colors.ENDC} - Read-only access")
    print()

    while True:
        choice = input("Enter role number (1-3): ").strip()

        if choice == "1":
            return "admin", None
        elif choice == "2":
            print("\nAvailable regions: North, South, East, West")
            region = input("Enter your region: ").strip()
            if region:
                return "manager", region
            else:
                print_error("Region is required for manager role")
        elif choice == "3":
            return "viewer", None
        else:
            print_error("Invalid choice. Please enter 1, 2, or 3.")


def display_role_info(role, region):
    """Display current role information."""
    print_info(f"Current Role: {role.upper()}")
    if region:
        print_info(f"Region: {region}")

    print("\nRole capabilities:")
    if role == "admin":
        print("  ✓ Full access to all data and operations")
        print("  ✓ Can view, insert, update, and delete across all regions")
    elif role == "manager":
        print(f"  ✓ Access to {region} region only")
        print("  ✓ Can view and modify data in your region")
        print("  ✗ Cannot access other regions")
    elif role == "viewer":
        print("  ✓ Can view all data across all regions")
        print("  ✗ Cannot insert, update, or delete any data")

    print()


def run_demo():
    """Run the interactive CLI demo."""
    # Print welcome banner
    print_header("Cognitive Database Agent - CLI Demo")

    print("Welcome to the Cognitive Database Agent!")
    print("This demo showcases AI-powered database interaction with")
    print("Row-Level Security (RLS) and multi-step planning.\n")

    # Test database connection
    print_info("Testing database connection...")
    if test_connection():
        print_success("✓ Database connection successful\n")
    else:
        print_error("✗ Database connection failed")
        print_error("Please check your .env file and database configuration")
        return

    # Check knowledge base
    try:
        stats = get_knowledge_stats()
        if stats["total_documents"] > 0:
            print_success(f"✓ Knowledge base loaded ({stats['total_documents']} documents)")
        else:
            print_warning("⚠ Knowledge base is empty")
            print_warning("  Run 'python -m backend.scripts.ingest_knowledge' to populate it")
    except:
        print_warning("⚠ Could not retrieve knowledge base stats")

    print()

    # Select role
    role, region = select_role()

    # Display role info
    print_header("Role Information")
    display_role_info(role, region)

    # Create agent
    print_info("Initializing cognitive agent...")
    agent = create_agent(role=role, region=region, verbose=True)
    print_success("✓ Agent ready\n")

    # Main chat loop
    print_header("Chat Interface")
    print("Commands:")
    print("  /role   - Switch role")
    print("  /help   - Show this help")
    print("  /exit   - Exit the demo")
    print()

    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.BOLD}You:{Colors.ENDC} ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() == "/exit":
                print_success("\nGoodbye!")
                break

            elif user_input.lower() == "/help":
                print("\nExample queries:")
                print("  • Show me all sales from 2022")
                print("  • What tables are available?")
                print("  • Delete sales records from 2021 (will be blocked for viewers)")
                print("  • Calculate total sales by region")
                print("  • Archive sales data from 2022")
                print()
                continue

            elif user_input.lower() == "/role":
                role, region = select_role()
                print_header("Role Information")
                display_role_info(role, region)
                agent = create_agent(role=role, region=region, verbose=True)
                print_success("✓ Agent reinitialized with new role\n")
                continue

            # Process query with agent
            print()
            print_info("🤖 Agent is thinking...\n")

            result = agent.run(user_input)

            # Display results
            print(f"\n{Colors.BOLD}Agent:{Colors.ENDC}")
            if result.get("success"):
                print_success(result.get("response", "No response"))

                # Display intermediate steps if available
                if result.get("intermediate_steps"):
                    print(f"\n{Colors.OKCYAN}Thought Process:{Colors.ENDC}")
                    for i, step in enumerate(result["intermediate_steps"], 1):
                        if len(step) >= 2:
                            action = step[0]
                            observation = step[1]
                            print(f"  Step {i}: {action.tool}")
                            print(f"    Input: {str(action.tool_input)[:100]}")
                            print(f"    Result: {str(observation)[:200]}...")
            else:
                print_error(f"Error: {result.get('error', 'Unknown error')}")

            print()

        except KeyboardInterrupt:
            print_success("\n\nGoodbye!")
            break
        except Exception as e:
            print_error(f"\nError: {e}\n")


def main():
    """Main entry point."""
    try:
        run_demo()
    except Exception as e:
        print_error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
