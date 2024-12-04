<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="/">
        <html>
            <head>
                <title>System Terms</title>
                <style>
                    table {
                        border: 1px solid gray;
                        border-collapse: collapse;
                        padding: 4px;
                    }
                    tr {
                    }
                    td, th {
                        border: 1px solid gray;
                        padding: 6px;
                    }
                </style>
            </head>
            <body>
                <xsl:apply-templates />
            </body>
        </html>
    </xsl:template>
    <xsl:template match="navigation_strategies">
        <h1>System Terms</h1>
        <table>
            <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Units</th>
                <th>Alt Units</th>
            </tr>
            <xsl:apply-templates select="system_terms">
                <xsl:sort select="term/@name" />
            </xsl:apply-templates>
        </table>
    </xsl:template>
    <xsl:template match="term">
        <tr>
            <td><xsl:value-of select="@name" /><br /></td>
            <td><xsl:value-of select="@description" /><br /></td>
            <td><xsl:value-of select="@units" /><br /></td>
            <td><xsl:value-of select="@alt_units" /><br /></td>
        </tr>
    </xsl:template>
</xsl:stylesheet>