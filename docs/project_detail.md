I’m looking to have a small Windows-desktop application built that lets our team manage fuel usage and billing in one place. The idea is simple:

• I drag-and-drop three files into the program—our monthly fuel statement, each branch’s litres sheet (tracked by litres only) and the Cars+ export that shows what we’ve billed.
• The app matches the data, flags any litres we haven’t charged for, and stores everything so I can drill down by branch.
• When I pick a branch from a dropdown, I want to see a clear on-screen report and be able to click “Export” to save that branch’s report as a PDF for follow-up.

Required file formats are Excel & PDF, so the import routine needs to parse both reliably. The finished build should run on any modern Windows PC without extra installs—an .exe with an embedded runtime or a lightweight installer is fine—and include a quick user guide.

Deliverables:
1. Compiled Windows application (installer or portable .exe).
2. Source code in a well-known language (C#, Python, or similar) so we can maintain it.
3. PDF export template that matches our current stationery.
4. Brief setup/user document.

I’ll test by uploading real files, selecting several branches and confirming that the generated PDFs reconcile with our manual process. Let me know your preferred tech stack and how quickly you can turn a working prototype.