# Goodman Pressure Washing Website

## Static quote form setup

This site is now set up to use a static form service such as Formspree so it can work on GitHub Pages without a running Python backend.

### What to change

1. Create a free account at Formspree.
2. Create a new form.
3. Copy the form endpoint URL.
4. Replace the action in [quote.html](quote.html) with your real form endpoint.

Example:

```html
<form class="quote-form" action="https://formspree.io/f/your-form-id" method="POST">
```

### Notes

- The local Python backend is no longer needed for the published site.
- Submissions will be handled by the form service instead of a local server.
- Your site can remain fully static and still receive quote requests.
