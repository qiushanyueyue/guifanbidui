/**
 * Opens a new tab searching csres.com with GBK encoding.
 * Uses a hidden form submission to handle the charset conversion.
 */
export const openCsresSearch = (keyword: string) => {
    // Create form
    const form = document.createElement('form');
    form.method = 'GET';
    form.action = 'http://www.csres.com/s.jsp';
    form.acceptCharset = 'gb2312';
    form.target = '_blank';
    form.style.display = 'none';

    // Input
    const input = document.createElement('input');
    input.type = 'text';
    input.name = 'keyword';
    input.value = keyword;
    form.appendChild(input);

    // Append to body, submit, remove
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
};
