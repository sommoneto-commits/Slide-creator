#!/usr/bin/env python3
"""
Slide Creator - CLI Main Entrypoint
Interactive command-line interface for creating presentations from storylines.
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from app.models import (
    FlowState,
    StorylineInput,
    StorylineReview,
    SlideOutline,
    SlideSpec,
    Session,
)
from app.config_manager import ConfigManager, get_config

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("slide_creator.log"),
        logging.StreamHandler() if os.getenv("DEBUG") else logging.NullHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Rich console for beautiful output
console = Console()


class SlideCreatorCLI:
    """Interactive CLI for Slide Creator."""

    def __init__(self):
        self.config = get_config()
        self.orchestrator = None  # Initialize after API key check
        self.session: Optional[Session] = None

    def run(self):
        """Main entry point."""
        self._show_welcome()

        # Check and prompt for API keys on startup
        if not self._check_api_keys():
            return

        # Initialize orchestrator after API keys are set
        self._init_orchestrator()

        while True:
            try:
                action = self._show_main_menu()

                if action == "new":
                    self._new_session()
                elif action == "resume":
                    self._resume_session()
                elif action == "list":
                    self._list_sessions()
                elif action == "settings":
                    self._settings_menu()
                elif action == "exit":
                    self._exit()
                    break
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted. Use 'exit' to quit properly.[/yellow]")
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                logger.exception("Error in main loop")

    def _init_orchestrator(self):
        """Initialize the orchestrator (call after API keys are configured)."""
        from app.orchestrator import Orchestrator
        self.orchestrator = Orchestrator()

    def _check_api_keys(self) -> bool:
        """Check if API keys are configured, prompt if not."""
        if not self.config.is_openai_configured():
            console.print("\n[yellow]OpenAI API Key not configured.[/yellow]")
            console.print("[dim]You need an OpenAI API key to use Slide Creator.[/dim]\n")

            if not self._prompt_openai_key():
                console.print("[red]OpenAI API key is required. Exiting.[/red]")
                return False

        # Gamma is optional - just inform if not configured
        if not self.config.is_gamma_configured():
            console.print("\n[dim]Gamma API not configured. Using mock mode for visual generation.[/dim]")
            console.print("[dim]You can configure it later in Settings.[/dim]\n")

        return True

    def _prompt_openai_key(self) -> bool:
        """Prompt user to enter OpenAI API key."""
        console.print("[bold]Enter your OpenAI API Key[/bold]")
        console.print("[dim]Get your key from: https://platform.openai.com/api-keys[/dim]\n")

        key = Prompt.ask("OpenAI API Key", password=True)

        if not key:
            return False

        # Validate format
        is_valid, message = self.config.validate_openai_key(key)
        if not is_valid:
            console.print(f"[yellow]Warning: {message}[/yellow]")
            if not Confirm.ask("Save anyway?"):
                return False

        self.config.set_openai_api_key(key)
        console.print("[green]OpenAI API key saved successfully![/green]")
        return True

    def _prompt_gamma_key(self) -> bool:
        """Prompt user to enter Gamma API key."""
        console.print("\n[bold]Enter your Gamma API Key (optional)[/bold]")
        console.print("[dim]Leave empty to use mock mode[/dim]\n")

        key = Prompt.ask("Gamma API Key (or press Enter to skip)", password=True, default="")

        if not key:
            self.config.set_gamma_use_mock(True)
            console.print("[yellow]Using Gamma mock mode.[/yellow]")
            return True

        self.config.set_gamma_api_key(key)
        console.print("[green]Gamma API key saved successfully![/green]")
        return True

    def _show_welcome(self):
        """Display welcome message."""
        welcome = """
# Slide Creator

AI-powered presentation generator with top-tier consulting methodology.

Transform your storyline into a professional presentation through:
1. Partner Review (strategic feedback)
2. Slide Outline (structured deck)
3. Slide Design (framework-based)
4. Visual Generation (Gamma)
5. PPTX Export
        """
        console.print(Panel(Markdown(welcome), title="Welcome", border_style="blue"))

    def _show_main_menu(self) -> str:
        """Show main menu and get user choice."""
        console.print("\n[bold]Main Menu[/bold]")
        console.print("  [cyan]new[/cyan]      - Start a new presentation")
        console.print("  [cyan]resume[/cyan]   - Resume an existing session")
        console.print("  [cyan]list[/cyan]     - List all sessions")
        console.print("  [cyan]settings[/cyan] - Configure API keys and settings")
        console.print("  [cyan]exit[/cyan]     - Exit the application")

        choice = Prompt.ask(
            "\nWhat would you like to do?",
            choices=["new", "resume", "list", "settings", "exit"],
            default="new",
        )
        return choice

    def _settings_menu(self):
        """Display and manage settings."""
        while True:
            console.print("\n" + "=" * 60)
            console.print("[bold cyan]Settings[/bold cyan]")
            console.print("=" * 60 + "\n")

            # Display current settings
            settings = self.config.get_all_settings()

            table = Table(title="Current Configuration", box=box.ROUNDED)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("OpenAI API Key", settings["openai_api_key"])
            table.add_row("OpenAI Model", settings["openai_model"])
            table.add_row("Gamma API Key", settings["gamma_api_key"])
            table.add_row("Gamma Mock Mode", "Enabled" if settings["gamma_use_mock"] else "Disabled")
            table.add_row("Output Directory", settings["output_dir"])

            console.print(table)

            # Menu options
            console.print("\n[bold]Options:[/bold]")
            console.print("  [cyan]1[/cyan] - Change OpenAI API Key")
            console.print("  [cyan]2[/cyan] - Change OpenAI Model")
            console.print("  [cyan]3[/cyan] - Change Gamma API Key")
            console.print("  [cyan]4[/cyan] - Toggle Gamma Mock Mode")
            console.print("  [cyan]5[/cyan] - Back to main menu")

            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"], default="5")

            if choice == "1":
                self._change_openai_key()
            elif choice == "2":
                self._change_openai_model()
            elif choice == "3":
                self._change_gamma_key()
            elif choice == "4":
                self._toggle_gamma_mock()
            elif choice == "5":
                break

            # Reinitialize orchestrator if API keys changed
            if choice in ["1", "3"]:
                self._init_orchestrator()

    def _change_openai_key(self):
        """Change OpenAI API key."""
        console.print("\n[bold]Change OpenAI API Key[/bold]")
        current = self.config.get_openai_api_key()
        if current:
            console.print(f"[dim]Current: {self.config._mask_key(current)}[/dim]")

        key = Prompt.ask("New OpenAI API Key (or press Enter to cancel)", password=True, default="")

        if key:
            is_valid, message = self.config.validate_openai_key(key)
            if not is_valid:
                console.print(f"[yellow]Warning: {message}[/yellow]")
                if not Confirm.ask("Save anyway?"):
                    return

            self.config.set_openai_api_key(key)
            console.print("[green]OpenAI API key updated![/green]")

    def _change_openai_model(self):
        """Change OpenAI model."""
        console.print("\n[bold]Change OpenAI Model[/bold]")
        current = self.config.get_openai_model()
        console.print(f"[dim]Current: {current}[/dim]")

        console.print("\n[dim]Available models: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo[/dim]")
        model = Prompt.ask("New model", default=current)

        if model and model != current:
            self.config.set_openai_model(model)
            console.print(f"[green]Model changed to: {model}[/green]")

    def _change_gamma_key(self):
        """Change Gamma API key."""
        console.print("\n[bold]Change Gamma API Key[/bold]")
        current = self.config.get_gamma_api_key()
        if current:
            console.print(f"[dim]Current: {self.config._mask_key(current)}[/dim]")

        key = Prompt.ask("New Gamma API Key (or press Enter to use mock mode)", password=True, default="")

        if key:
            self.config.set_gamma_api_key(key)
            self.config.set_gamma_use_mock(False)
            console.print("[green]Gamma API key updated! Mock mode disabled.[/green]")
        else:
            self.config.set_gamma_use_mock(True)
            console.print("[yellow]Using Gamma mock mode.[/yellow]")

    def _toggle_gamma_mock(self):
        """Toggle Gamma mock mode."""
        current = self.config.get_gamma_use_mock()
        new_value = not current

        if not new_value and not self.config.get_gamma_api_key():
            console.print("[red]Cannot disable mock mode without a Gamma API key.[/red]")
            console.print("[dim]Please set a Gamma API key first.[/dim]")
            return

        self.config.set_gamma_use_mock(new_value)
        status = "enabled" if new_value else "disabled"
        console.print(f"[green]Gamma mock mode {status}.[/green]")

    def _new_session(self):
        """Start a new session."""
        console.print("\n[bold cyan]Starting New Session[/bold cyan]\n")

        # Get storyline
        console.print("[dim]Enter your storyline (multi-line input, press Enter twice to finish):[/dim]")
        storyline = self._get_multiline_input()

        if not storyline.strip():
            console.print("[red]Storyline cannot be empty.[/red]")
            return

        # Get optional parameters
        console.print("\n[dim]Optional parameters (press Enter to skip):[/dim]")

        target_audience = Prompt.ask("Target audience", default="")
        duration = Prompt.ask("Duration (minutes)", default="")
        tone = Prompt.ask("Tone of voice (formal/conversational/etc)", default="")
        brand = Prompt.ask("Brand constraints", default="")

        # Create input model
        storyline_input = StorylineInput(
            storyline=storyline,
            target_audience=target_audience if target_audience else None,
            duration_minutes=int(duration) if duration.isdigit() else None,
            tone_of_voice=tone if tone else None,
            brand_constraints=brand if brand else None,
        )

        # Create session
        self.session = self.orchestrator.create_session(storyline[:50])
        console.print(f"\n[green]Session created: {self.session.session_id}[/green]")

        # Run the flow
        self._run_flow(storyline_input)

    def _resume_session(self):
        """Resume an existing session."""
        sessions = self.orchestrator.list_sessions()

        if not sessions:
            console.print("[yellow]No sessions found.[/yellow]")
            return

        # Show sessions
        table = Table(title="Available Sessions", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("State", style="yellow")
        table.add_column("Slides", style="green")
        table.add_column("Updated", style="dim")

        for s in sessions[:10]:  # Show latest 10
            table.add_row(
                s["session_id"],
                s["state"],
                str(s["slide_count"]),
                s["updated_at"][:16] if s["updated_at"] else "N/A",
            )

        console.print(table)

        # Get session ID
        session_id = Prompt.ask("\nEnter session ID to resume")
        self.session = self.orchestrator.load_session(session_id)

        if not self.session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            return

        console.print(f"[green]Session loaded: {session_id}[/green]")
        self._continue_flow()

    def _list_sessions(self):
        """List all sessions."""
        sessions = self.orchestrator.list_sessions()

        if not sessions:
            console.print("[yellow]No sessions found.[/yellow]")
            return

        table = Table(title="All Sessions", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("State", style="yellow")
        table.add_column("Slides", style="green")
        table.add_column("Created", style="dim")
        table.add_column("Updated", style="dim")

        for s in sessions:
            table.add_row(
                s["session_id"],
                s["state"],
                str(s["slide_count"]),
                s["created_at"][:16] if s["created_at"] else "N/A",
                s["updated_at"][:16] if s["updated_at"] else "N/A",
            )

        console.print(table)

    def _run_flow(self, storyline_input: StorylineInput):
        """Run the complete flow for a new session."""
        # Step A: Partner Review
        if not self._step_partner_review(storyline_input):
            return

        # Step B: Slide Outline
        if not self._step_slide_outline():
            return

        # Steps C & D: Slide Spec and Gamma for each slide
        if not self._step_process_all_slides():
            return

        # Step E: Export
        self._step_export()

    def _continue_flow(self):
        """Continue flow from current state."""
        if not self.session:
            return

        state = self.session.current_state
        console.print(f"[dim]Current state: {state.value}[/dim]")

        if state == FlowState.INIT:
            console.print("[yellow]Session not started. Please start a new session.[/yellow]")
        elif state == FlowState.PARTNER_REVIEW:
            # Need storyline input to continue
            console.print("[yellow]Resuming from partner review...[/yellow]")
            if self.session.storyline_input:
                self._run_flow(self.session.storyline_input)
        elif state == FlowState.SLIDE_OUTLINE:
            if not self._step_slide_outline():
                return
            if not self._step_process_all_slides():
                return
            self._step_export()
        elif state in [FlowState.SLIDE_SPEC, FlowState.GAMMA_GENERATION]:
            if not self._step_process_all_slides():
                return
            self._step_export()
        elif state == FlowState.EXPORT:
            self._step_export()
        elif state == FlowState.COMPLETED:
            console.print("[green]Session already completed![/green]")
            if self.session.output_file:
                console.print(f"Output: {self.session.output_file}")
        elif state == FlowState.ABORTED:
            console.print("[red]Session was aborted.[/red]")

    # ============ STEP A: PARTNER REVIEW ============

    def _step_partner_review(self, storyline_input: StorylineInput) -> bool:
        """Execute partner review step."""
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]STEP A: Partner Review[/bold cyan]")
        console.print("=" * 60 + "\n")

        iteration = 0
        max_iterations = self.orchestrator.max_storyline_iterations

        while iteration < max_iterations:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Generating partner review...", total=None)
                review = self.orchestrator.run_partner_review(self.session, storyline_input)

            self._display_review(review)

            # Get user action
            action = self._prompt_user_action(
                "Review your storyline feedback:",
                ["approve", "edit", "retry", "abort"],
            )

            if action == "approve":
                console.print("[green]Storyline approved. Moving to outline generation.[/green]")
                return True
            elif action == "edit":
                console.print("\n[dim]Enter updated storyline:[/dim]")
                new_storyline = self._get_multiline_input()
                if new_storyline.strip():
                    self.orchestrator.update_storyline(self.session, new_storyline)
                    storyline_input.storyline = new_storyline
                console.print("[green]Storyline updated.[/green]")
            elif action == "retry":
                console.print("[yellow]Regenerating review...[/yellow]")
            elif action == "abort":
                self.orchestrator.abort_session(self.session)
                console.print("[red]Session aborted.[/red]")
                return False

            iteration += 1

        console.print(f"[yellow]Maximum iterations ({max_iterations}) reached. Proceeding with current storyline.[/yellow]")
        return True

    def _display_review(self, review: StorylineReview):
        """Display the partner review."""
        console.print(Panel(review.overall_assessment, title="Overall Assessment", border_style="blue"))

        # Strengths
        if review.strengths:
            console.print("\n[bold green]Strengths:[/bold green]")
            for s in review.strengths:
                console.print(f"  [green]✓[/green] {s}")

        # Gaps
        if review.gaps:
            console.print("\n[bold yellow]Gaps:[/bold yellow]")
            for g in review.gaps:
                console.print(f"  [yellow]![/yellow] {g}")

        # Risks
        if review.risks:
            console.print("\n[bold red]Risks:[/bold red]")
            for r in review.risks:
                console.print(f"  [red]⚠[/red] {r}")

        # Recommendations
        if review.recommendations:
            console.print("\n[bold cyan]Recommendations:[/bold cyan]")
            for r in review.recommendations:
                console.print(f"  [cyan]→[/cyan] {r}")

        # Questions
        if review.clarifying_questions:
            console.print("\n[bold magenta]Clarifying Questions:[/bold magenta]")
            for q in review.clarifying_questions:
                console.print(f"  [magenta]?[/magenta] {q}")

        # Suggested rewrite
        if review.suggested_rewrite:
            console.print("\n[bold]Suggested Rewrite:[/bold]")
            console.print(Panel(review.suggested_rewrite, border_style="dim"))

    # ============ STEP B: SLIDE OUTLINE ============

    def _step_slide_outline(self) -> bool:
        """Execute slide outline step."""
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]STEP B: Slide Outline[/bold cyan]")
        console.print("=" * 60 + "\n")

        iteration = 0
        max_iterations = self.orchestrator.max_outline_iterations

        # Generate initial outline if not present
        if not self.session.current_outline:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Generating slide outline...", total=None)
                self.orchestrator.generate_slide_outline(self.session)

        while iteration < max_iterations:
            self._display_outline(self.session.current_outline)

            # Get user action
            action = self._prompt_user_action(
                "Review slide outline:",
                ["approve", "edit", "add", "delete", "retry", "abort"],
            )

            if action == "approve":
                console.print("[green]Outline approved. Moving to slide design.[/green]")
                return True
            elif action == "edit":
                self._edit_outline_interactive()
            elif action == "add":
                self._add_slide_interactive()
            elif action == "delete":
                self._delete_slide_interactive()
            elif action == "retry":
                feedback = Prompt.ask("What should be changed?")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    progress.add_task("Revising outline...", total=None)
                    self.orchestrator.revise_slide_outline(self.session, feedback)
            elif action == "abort":
                self.orchestrator.abort_session(self.session)
                console.print("[red]Session aborted.[/red]")
                return False

            iteration += 1

        console.print(f"[yellow]Maximum iterations ({max_iterations}) reached. Proceeding with current outline.[/yellow]")
        return True

    def _display_outline(self, outline: SlideOutline):
        """Display the slide outline."""
        console.print(Panel(f"[bold]{outline.deck_title}[/bold]", title="Deck Title", border_style="blue"))

        if outline.deck_subtitle:
            console.print(f"[dim]Subtitle: {outline.deck_subtitle}[/dim]")

        console.print(f"\n[bold]Slides ({len(outline.slides)}):[/bold]\n")

        for i, slide in enumerate(outline.slides, 1):
            console.print(f"[cyan]{slide.slide_id}[/cyan] [bold]{slide.title}[/bold]")
            console.print(f"  [dim]Objective:[/dim] {slide.objective}")
            console.print(f"  [dim]Key Message:[/dim] {slide.key_message}")
            if slide.bullets:
                console.print("  [dim]Bullets:[/dim]")
                for b in slide.bullets[:3]:
                    console.print(f"    • {b}")
                if len(slide.bullets) > 3:
                    console.print(f"    [dim]... and {len(slide.bullets) - 3} more[/dim]")
            console.print()

    def _edit_outline_interactive(self):
        """Interactive outline editing."""
        slide_id = Prompt.ask("Which slide to edit? (e.g., S01)")

        # Find slide
        slide = None
        for s in self.session.current_outline.slides:
            if s.slide_id == slide_id:
                slide = s
                break

        if not slide:
            console.print(f"[red]Slide {slide_id} not found.[/red]")
            return

        console.print(f"\nEditing [cyan]{slide_id}[/cyan]: {slide.title}")
        console.print("[dim]Press Enter to keep current value[/dim]\n")

        updates = {}

        new_title = Prompt.ask("Title", default=slide.title)
        if new_title != slide.title:
            updates["title"] = new_title

        new_obj = Prompt.ask("Objective", default=slide.objective)
        if new_obj != slide.objective:
            updates["objective"] = new_obj

        new_msg = Prompt.ask("Key message", default=slide.key_message)
        if new_msg != slide.key_message:
            updates["key_message"] = new_msg

        if updates:
            self.orchestrator.edit_slide_in_outline(self.session, slide_id, updates)
            console.print("[green]Slide updated.[/green]")

    def _add_slide_interactive(self):
        """Interactive slide addition."""
        console.print("\n[bold]Add New Slide[/bold]")

        title = Prompt.ask("Title")
        objective = Prompt.ask("Objective")
        key_message = Prompt.ask("Key message")
        bullets_str = Prompt.ask("Bullets (comma-separated)")
        bullets = [b.strip() for b in bullets_str.split(",") if b.strip()]

        after = Prompt.ask("Insert after slide (e.g., S01, or leave blank for end)", default="")

        slide_data = {
            "title": title,
            "objective": objective,
            "key_message": key_message,
            "bullets": bullets,
            "evidence_needed": [],
        }

        self.orchestrator.add_slide_to_outline(
            self.session,
            slide_data,
            after_slide_id=after if after else None,
        )
        console.print("[green]Slide added.[/green]")

    def _delete_slide_interactive(self):
        """Interactive slide deletion."""
        slide_id = Prompt.ask("Which slide to delete? (e.g., S01)")

        if Confirm.ask(f"Delete slide {slide_id}?"):
            self.orchestrator.remove_slide_from_outline(self.session, slide_id)
            console.print(f"[green]Slide {slide_id} deleted.[/green]")

    # ============ STEPS C & D: PROCESS SLIDES ============

    def _step_process_all_slides(self) -> bool:
        """Process all slides through spec and gamma generation."""
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]STEPS C & D: Slide Design & Generation[/bold cyan]")
        console.print("=" * 60 + "\n")

        total_slides = len(self.session.current_outline.slides)

        for i, slide in enumerate(self.session.current_outline.slides):
            progress = self.session.slide_progress[i]

            console.print(f"\n[bold]Processing Slide {i + 1}/{total_slides}: {slide.slide_id} - {slide.title}[/bold]")

            # Step C: Slide Spec
            if not progress.spec_approved:
                if not self._process_slide_spec(i):
                    return False

            # Step D: Gamma Generation
            if not progress.gamma_approved:
                if not self._process_slide_gamma(i):
                    return False

        console.print("\n[green]All slides processed successfully![/green]")
        return True

    def _process_slide_spec(self, slide_index: int) -> bool:
        """Process slide specification."""
        progress = self.session.slide_progress[slide_index]
        iteration = 0
        max_iterations = self.orchestrator.max_slide_spec_iterations

        # Generate spec if not present
        if not progress.current_spec:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as prog:
                prog.add_task("Generating slide spec...", total=None)
                self.orchestrator.generate_slide_spec(self.session, slide_index)

        while iteration < max_iterations:
            self._display_slide_spec(progress.current_spec)

            action = self._prompt_user_action(
                "Review slide design spec:",
                ["approve", "retry", "skip", "abort"],
            )

            if action == "approve":
                self.orchestrator.approve_slide_spec(self.session, slide_index)
                console.print("[green]Spec approved.[/green]")
                return True
            elif action == "retry":
                feedback = Prompt.ask("What should be changed?")
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as prog:
                    prog.add_task("Revising spec...", total=None)
                    self.orchestrator.revise_slide_spec(self.session, slide_index, feedback)
            elif action == "skip":
                # Approve and skip gamma
                self.orchestrator.approve_slide_spec(self.session, slide_index)
                progress.gamma_approved = True
                self.orchestrator.save_session(self.session)
                console.print("[yellow]Slide skipped (will use spec without Gamma).[/yellow]")
                return True
            elif action == "abort":
                self.orchestrator.abort_session(self.session)
                return False

            iteration += 1

        # Auto-approve after max iterations
        self.orchestrator.approve_slide_spec(self.session, slide_index)
        return True

    def _display_slide_spec(self, spec: SlideSpec):
        """Display slide specification."""
        console.print(Panel(
            f"[bold]{spec.title}[/bold]\n\n"
            f"[cyan]Framework:[/cyan] {spec.framework_name} ({spec.framework_id})\n"
            f"[dim]Rationale:[/dim] {spec.rationale}",
            title=f"Slide {spec.slide_id}",
            border_style="blue",
        ))

        console.print(f"\n[bold]Headline:[/bold] {spec.copy.headline}")

        if spec.copy.body:
            console.print("\n[bold]Body:[/bold]")
            for b in spec.copy.body:
                console.print(f"  • {b}")

        if spec.layout.sections:
            console.print("\n[bold]Layout Sections:[/bold]")
            for section in spec.layout.sections:
                console.print(f"  [{section.content_type}] {section.name}: {section.content[:80]}...")

        if spec.data_viz and spec.data_viz.type != "none":
            console.print(f"\n[bold]Data Viz:[/bold] {spec.data_viz.type}")

        if spec.copy.footnotes:
            console.print(f"\n[dim]Footnotes: {', '.join(spec.copy.footnotes)}[/dim]")

    def _process_slide_gamma(self, slide_index: int) -> bool:
        """Process Gamma generation for a slide."""
        progress = self.session.slide_progress[slide_index]
        iteration = 0
        max_iterations = self.orchestrator.max_gamma_iterations

        while iteration < max_iterations:
            # Generate with Gamma
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as prog:
                prog.add_task("Generating slide with Gamma...", total=None)
                result = self.orchestrator.generate_with_gamma(self.session, slide_index)

            # Display result
            if result.success:
                console.print(f"\n[green]Gamma generation successful![/green]")
                console.print(f"  Gamma ID: {result.gamma_id}")
                if result.image_url:
                    console.print(f"  Preview: {result.image_url}")

                # Show structured content summary if available
                if result.structured_content:
                    elements = result.structured_content.get("elements", [])
                    console.print(f"  Elements: {len(elements)}")

                action = self._prompt_user_action(
                    "Review generated slide:",
                    ["approve", "retry", "abort"],
                )

                if action == "approve":
                    self.orchestrator.approve_gamma_result(self.session, slide_index)
                    console.print("[green]Slide approved.[/green]")
                    return True
                elif action == "retry":
                    feedback = Prompt.ask("What should be changed?")
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console,
                    ) as prog:
                        prog.add_task("Regenerating with feedback...", total=None)
                        result = self.orchestrator.retry_gamma_with_feedback(
                            self.session, slide_index, feedback
                        )
                elif action == "abort":
                    self.orchestrator.abort_session(self.session)
                    return False
            else:
                console.print(f"\n[red]Gamma generation failed: {result.error_message}[/red]")

                if Confirm.ask("Retry?"):
                    pass  # Will retry in next iteration
                else:
                    # Approve without Gamma result
                    progress.gamma_approved = True
                    self.orchestrator.save_session(self.session)
                    console.print("[yellow]Proceeding without Gamma for this slide.[/yellow]")
                    return True

            iteration += 1

        console.print(f"[yellow]Maximum Gamma iterations reached. Proceeding.[/yellow]")
        progress.gamma_approved = True
        self.orchestrator.save_session(self.session)
        return True

    # ============ STEP E: EXPORT ============

    def _step_export(self):
        """Execute export step."""
        console.print("\n" + "=" * 60)
        console.print("[bold cyan]STEP E: Export to PPTX[/bold cyan]")
        console.print("=" * 60 + "\n")

        # Show summary
        summary = self.orchestrator.get_session_summary(self.session)
        console.print(f"Total slides: {summary['total_slides']}")
        console.print(f"Completion: {summary['completion_percentage']:.0f}%")

        if not Confirm.ask("\nExport presentation?"):
            return

        author = Prompt.ask("Author name", default="Slide Creator")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as prog:
            prog.add_task("Exporting to PPTX...", total=None)
            filepath = self.orchestrator.export_to_pptx(self.session, author=author)

        console.print(f"\n[bold green]Presentation exported successfully![/bold green]")
        console.print(f"File: {filepath}")

    # ============ UTILITIES ============

    def _prompt_user_action(self, message: str, choices: list[str]) -> str:
        """Prompt user to choose an action."""
        console.print(f"\n[bold]{message}[/bold]")
        for c in choices:
            desc = {
                "approve": "Accept and continue",
                "edit": "Make changes",
                "retry": "Regenerate with feedback",
                "add": "Add a slide",
                "delete": "Remove a slide",
                "skip": "Skip this step",
                "abort": "Cancel the session",
            }.get(c, c)
            console.print(f"  [cyan]{c}[/cyan] - {desc}")

        return Prompt.ask("Action", choices=choices)

    def _get_multiline_input(self) -> str:
        """Get multi-line input from user."""
        lines = []
        empty_count = 0

        while True:
            try:
                line = input()
                if line == "":
                    empty_count += 1
                    if empty_count >= 2:
                        break
                    lines.append(line)
                else:
                    empty_count = 0
                    lines.append(line)
            except EOFError:
                break

        return "\n".join(lines).strip()

    def _exit(self):
        """Exit the application."""
        console.print("\n[bold]Thank you for using Slide Creator![/bold]")
        if self.session and self.session.current_state not in [FlowState.COMPLETED, FlowState.ABORTED]:
            console.print(f"[dim]Session saved: {self.session.session_id}[/dim]")


def main():
    """Main entry point."""
    cli = SlideCreatorCLI()
    cli.run()


if __name__ == "__main__":
    main()
