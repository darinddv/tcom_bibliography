from django.core.management.base import BaseCommand
from core.models.publications import Publication
from core.models.extraction import ExtractionRecord
from core.services.llm_extraction import run_llm_extraction


class Command(BaseCommand):
    help = 'Run LLM extraction on publications that do not yet have one.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Re-run LLM extraction on all publications, even those that already have one.',
        )
        parser.add_argument(
            '--doi',
            type=str,
            help='Run LLM extraction on a single publication by DOI.',
        )

    def handle(self, *args, **options):
        if options['doi']:
            publications = Publication.objects.filter(doi=options['doi'])
            if not publications.exists():
                self.stdout.write(self.style.ERROR(f'No publication found with DOI: {options["doi"]}'))
                return
        elif options['all']:
            publications = Publication.objects.all()
        else:
            # Only publications without an existing LLM extraction
            existing_llm_pubs = ExtractionRecord.objects.filter(
                reviewer_type='llm'
            ).values_list('publication_id', flat=True)
            publications = Publication.objects.exclude(pk__in=existing_llm_pubs)

        total = publications.count()
        if total == 0:
            self.stdout.write('No publications to process.')
            return

        self.stdout.write(f'Processing {total} publication(s)...\n')
        success = 0
        failed = 0

        for pub in publications:
            try:
                extraction = run_llm_extraction(pub)
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ {pub.title[:70]}')
                )
                success += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ {pub.title[:70]}\n    Error: {e}')
                )
                failed += 1

        self.stdout.write(f'\nDone. {success} succeeded, {failed} failed.')