<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:variable name="apos">'</xsl:variable>
	<xsl:variable name="create">'create'</xsl:variable>
	<xsl:variable name="dupe">'duplicate'</xsl:variable>
	<xsl:variable name="view">'view'</xsl:variable>
	
	<xsl:template match="/">
		<ul id="settings-menu-list">
			<xsl:apply-templates />
		</ul>
	</xsl:template>
	<!-- swallow extraneous white space -->
	<xsl:template match="text()" />
	<!-- <items> with <item> children becomes <ul> -->
	<xsl:template match="blueprints" />
    <!-- swallow blueprints -->
	<xsl:template match="profiles">
		<li>
			<div>
                <xsl:text>1 Profiles</xsl:text>
			</div>
			<ul>
                <xsl:attribute name="id">
                     <xsl:text>sm1</xsl:text>
                </xsl:attribute>
   				<xsl:apply-templates select="profile">
                    <xsl:with-param name="index">1.</xsl:with-param> 
				</xsl:apply-templates>
                <xsl:call-template name="add-profile">
                    <xsl:with-param name="index">1.</xsl:with-param>
                </xsl:call-template>
			</ul>
		</li>
	</xsl:template>
	<xsl:template match="mowers">
		<li>
			<div>
				<xsl:text>2 Mowers</xsl:text>
			</div>
			<ul>
	            <xsl:attribute name="id">
                     <xsl:text>sm2</xsl:text>
   	            </xsl:attribute>
				<xsl:apply-templates select="mower">
                    <xsl:with-param name="index">2.</xsl:with-param>
                </xsl:apply-templates> 
			    <xsl:call-template name="add-mower">
                    <xsl:with-param name="index">2.</xsl:with-param>
			    </xsl:call-template>
			</ul>
		</li>
	</xsl:template>
	<xsl:template match="navigation_strategies">
		<li>
			<div>
                <xsl:text>3 Strategies</xsl:text>
			</div>
			<ul>
	            <xsl:attribute name="id">
                     <xsl:text>sm3</xsl:text>
	            </xsl:attribute>
				<xsl:apply-templates select="strategy">
                    <xsl:with-param name="index">3.</xsl:with-param>
				</xsl:apply-templates>
                <xsl:call-template name="add-strategy">
                    <xsl:with-param name="index">3.</xsl:with-param>
                </xsl:call-template>
			</ul>
		</li>
	</xsl:template>
	<xsl:template match="pairings">
        <li>
            <div>
                <xsl:text>4 Pairings</xsl:text>
            </div>
            <ul>
	            <xsl:attribute name="id">
                     <xsl:text>sm4</xsl:text>
	            </xsl:attribute>
                <xsl:apply-templates select="pairing">
                    <xsl:with-param name="index">4.</xsl:with-param>
                </xsl:apply-templates>
                <xsl:call-template name="add-pairing">
                    <xsl:with-param name="index">4.</xsl:with-param>
                </xsl:call-template>
            </ul>
        </li>
    </xsl:template>
    <xsl:template match="measures">
        <li>
            <div>
                <xsl:text>5 Measures</xsl:text>
            </div>
            <ul>
                <xsl:attribute name="id">
                     <xsl:text>sm5</xsl:text>
                </xsl:attribute>
                <xsl:apply-templates select="scaled_measures/scaled">
                    <xsl:with-param name="index">5.1.</xsl:with-param>
                </xsl:apply-templates>
                <xsl:apply-templates select="setpoint_measures/setpoint">
                    <xsl:with-param name="index">5.2.</xsl:with-param>
                </xsl:apply-templates>
            </ul>
        </li>
    </xsl:template>

    <xsl:template name="add-profile">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '0')" />
        <xsl:variable name="xp"
            select="concat($apos, 'profiles', $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id,', $xp, ',', $create,');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <span>Add Profile</span>
            </a>
        </li>
    </xsl:template>
	<xsl:template match="profile">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
        <xsl:variable name="xp1"
            select="'profiles/profile[@name=&quot;'" />
        <xsl:variable name="xp2" select="@name" />
        <xsl:variable name="xp3"
            select="'&quot;]'" />
        <xsl:variable name="xp"
            select="concat($apos, $xp1, $xp2, $xp3, $apos)" />
		<li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
	            </xsl:attribute>
	            <xsl:attribute name="onclick">
	                <xsl:value-of
	                select="concat('renderForm(this.id, ', $xp, ');')" />
	            </xsl:attribute>
	            <xsl:value-of select="concat($id, '.')" />&#160;
				<xsl:value-of select="@name" />
            </a>&#160;
            <img src="/icons/bin.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('del(', $apos, 'sm', $id, $apos, ',', $xp, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Delete Profile</xsl:attribute>
            </img>&#160;
            <img src="/icons/copy.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('renderForm(', $apos, 'sm', $id, $apos, ',', $xp, ',', $dupe, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Duplicate Profile</xsl:attribute>
            </img>
		</li>
	</xsl:template>
	<xsl:template name="add-mower">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '0')" />
        <xsl:variable name="xp"
            select="concat($apos, 'mowers', $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id,', $xp, ',', $create,');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <span>Add Mower</span>
            </a>
        </li>
	</xsl:template>
	<xsl:template match="mower">
	    <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
		<xsl:variable name="xp"
			select="concat($apos, 'mowers/mower[@name=&quot;', @name, '&quot;]', $apos)" />
		<li>
			<a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
				<xsl:attribute name="onclick">
                    <xsl:value-of
					select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
				<xsl:value-of select="@name" />
			</a>&#160;
            <img src="/icons/bin.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('del(', $apos, 'sm', $id, $apos, ',', $xp, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Delete Mower</xsl:attribute>
            </img>&#160;
            <img src="/icons/copy.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('renderForm(', $apos, 'sm', $id, $apos, ',', $xp, ',', $dupe, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Duplicate Mower</xsl:attribute>
            </img>
		</li>
	</xsl:template>
    <xsl:template name="add-strategy">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '0')" />
        <xsl:variable name="xp"
            select="concat($apos, 'navigation_strategies', $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id,', $xp, ',', $create,');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <span>Add Strategy</span>
            </a>
        </li>
    </xsl:template>
	<xsl:template match="strategy">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
        <xsl:variable name="xp1"
            select="'navigation_strategies/strategy[@name=&quot;'" />
        <xsl:variable name="xp2" select="@name" />
        <xsl:variable name="xp3"
            select="'&quot;]'" />
        <xsl:variable name="xp"
            select="concat($apos, $xp1, $xp2, $xp3, $apos)" />
        <li>
            <xsl:value-of select="$id" />&#160;
            <img src="/icons/bin.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('del(', $apos, 'sm', $id, $apos, ',', $xp, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Delete Strategy</xsl:attribute>
            </img>&#160;
            <img src="/icons/copy.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('renderForm(', $apos, 'sm', $id, $apos, ',', $xp, ',', $dupe, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Duplicate Strategy</xsl:attribute>
            </img>&#160;
   			<div>
	            <xsl:attribute name="onclick">
	                <xsl:value-of
	                select="concat('renderForm(this.id, ', $xp, ');')" />
	            </xsl:attribute>

				<xsl:value-of select="@name" />
			</div>
			<ul>
	            <xsl:attribute name="id">
	                 <xsl:value-of select="concat('sm', $id)" />
	            </xsl:attribute>
				<xsl:apply-templates select="user_terms">
		            <xsl:with-param name="index">
		                <xsl:value-of select="concat($id, '.')" />
		            </xsl:with-param>
				</xsl:apply-templates>
                <xsl:apply-templates select="hybrid_terms">
                    <xsl:with-param name="index">
                        <xsl:value-of select="concat($id, '.')" />
                    </xsl:with-param>
                </xsl:apply-templates>
				<xsl:apply-templates select="rules">
		            <xsl:with-param name="index">
		                <xsl:value-of select="concat($id, '.')" />
		            </xsl:with-param>
				</xsl:apply-templates>
			</ul>
		</li>
	</xsl:template>
	
    <xsl:template match="user_terms">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '1')" />
        <li>
            <div>
                 <xsl:value-of select="$id" />&#160;
                 <xsl:text>User Terms</xsl:text>
            </div>
            <ul>
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>            
                <xsl:apply-templates select="term">
                    <xsl:with-param name="index">
                        <xsl:value-of select="concat($id, '.')" />
                    </xsl:with-param>
                </xsl:apply-templates>
                <xsl:call-template name="add-user-term">
                    <xsl:with-param name="index">
                        <xsl:value-of select="concat($id, '.')" />
                    </xsl:with-param>
                </xsl:call-template>
            </ul>
        </li>
    </xsl:template>
    
    <xsl:template match="hybrid_terms">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '1')" />
        <li>
            <div>
                 <xsl:value-of select="$id" />&#160;
                 <xsl:text>Hybrid Terms</xsl:text>
            </div>
            <ul>
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>            
                <xsl:apply-templates select="hybrid">
                    <xsl:with-param name="index">
                        <xsl:value-of select="concat($id, '.')" />
                    </xsl:with-param>
                </xsl:apply-templates>
            </ul>
        </li>
    </xsl:template>

    <xsl:template name="add-user-term">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '0')" />
        <xsl:variable name="xp1"
            select="'navigation_strategies/strategy[@name=&quot;'" />
        <xsl:variable name="xp2" select="../@name" />
        <xsl:variable name="xp3"
            select="'&quot;]/user_terms'" />
        <xsl:variable name="xp"
            select="concat($apos, $xp1, $xp2, $xp3, $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id,', $xp, ',', $create,');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <span>Add User Term</span>
            </a>
        </li>
    </xsl:template>

    <xsl:template match="term">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
        <xsl:variable name="xp1"
            select="'navigation_strategies/strategy[@name=&quot;'" />
        <xsl:variable name="xp2" select="../../@name" />
        <xsl:variable name="xp3"
            select="'&quot;]/user_terms/term[@name=&quot;'" />
        <xsl:variable name="xp4" select="'&quot;]'" />
        <xsl:variable name="xp"
            select="concat($apos, $xp1, $xp2, $xp3, @name, $xp4, $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <xsl:value-of select="@name" />
            </a>&#160;
            <img src="/icons/bin.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('del(', $apos, 'sm', $id, $apos, ',', $xp, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Delete Term</xsl:attribute>
            </img>&#160;
            <img src="/icons/copy.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('renderForm(', $apos, 'sm', $id, $apos, ',', $xp, ',', $dupe, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Duplicate Term</xsl:attribute>
            </img>
        </li>
    </xsl:template>
    
    <xsl:template match="hybrid">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
        <xsl:variable name="xp1"
            select="'navigation_strategies/strategy[@name=&quot;'" />
        <xsl:variable name="xp2" select="../../@name" />
        <xsl:variable name="xp3"
            select="'&quot;]/hybrid_terms/hybrid[@name=&quot;'" />
        <xsl:variable name="xp4" select="'&quot;]'" />
        <xsl:variable name="xp"
            select="concat($apos, $xp1, $xp2, $xp3, @name, $xp4, $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <xsl:value-of select="@name" />
            </a>
        </li>
    </xsl:template>
    
	<xsl:template match="rules">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '2')" />
		<li>
			<div>
			     <xsl:value-of select="$id" />&#160;
			     <xsl:text>Rules</xsl:text>
			</div>
			<ul>
	            <xsl:attribute name="id">
	                 <xsl:value-of select="concat('sm', $id)" />
	            </xsl:attribute>
				<xsl:apply-templates select="rule">
                    <xsl:with-param name="index">
                        <xsl:value-of select="concat($id, '.')" />
                    </xsl:with-param>
				</xsl:apply-templates>
	            <xsl:call-template name="add-rule">
	                <xsl:with-param name="index">
	                    <xsl:value-of select="concat($id, '.')" />
	                </xsl:with-param>
	            </xsl:call-template>
			</ul>
		</li>
	</xsl:template>
    <xsl:template name="add-rule">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '0')" />
        <xsl:variable name="xp1"
            select="'navigation_strategies/strategy[@name=&quot;'" />
        <xsl:variable name="xp2" select="../@name" />
        <xsl:variable name="xp3"
            select="'&quot;]/rules'" />
        <xsl:variable name="xp"
            select="concat($apos, $xp1, $xp2, $xp3, $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id,', $xp, ',', $create,');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <span>Add Rule</span>
            </a>
        </li>
    </xsl:template>
	<xsl:template match="rule">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
   		<xsl:variable name="xp1"
			select="'navigation_strategies/strategy[@name=&quot;'" />
		<xsl:variable name="xp2" select="../../@name" />
		<xsl:variable name="xp3"
			select="'&quot;]/rules/rule[@name=&quot;'" />
		<xsl:variable name="xp4" select="'&quot;]'" />
		<xsl:variable name="xp"
			select="concat($apos, $xp1, $xp2, $xp3, @name, $xp4, $apos)" />
		<li>
			<a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
				<xsl:attribute name="onclick">
                    <xsl:value-of
					select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
				<xsl:value-of select="@name" />
			</a>&#160;
            <img src="/icons/bin.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('del(', $apos, 'sm', $id, $apos, ',', $xp, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Delete Rule</xsl:attribute>
            </img>&#160;
            <img src="/icons/copy.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('renderForm(', $apos, 'sm', $id, $apos, ',', $xp, ',', $dupe, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Duplicate Rule</xsl:attribute>
            </img>
		</li>
	</xsl:template>
    <xsl:template name="add-pairing">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, '0')" />
        <xsl:variable name="xp"
            select="concat($apos, 'pairings', $apos)" />
        <li>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id,', $xp, ',', $create,');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <span>Add Pairing</span>
            </a>
        </li>
    </xsl:template>
	<xsl:template match="pairing">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
   		<xsl:variable name="xp"
			select="concat($apos, 'pairings/pairing[@name=&quot;', @name, '&quot;]', $apos)" />
		<li>
			<xsl:attribute name="title">
                <xsl:value-of select="@description" />
            </xsl:attribute>
			<a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
				<xsl:attribute name="onclick">
                    <xsl:value-of
					select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
				<xsl:value-of select="@name" />
			</a>&#160;
            <img src="/icons/bin.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('del(', $apos, 'sm', $id, $apos, ',', $xp, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Delete Pairing</xsl:attribute>
            </img>&#160;
            <img src="/icons/copy.svg">
                <xsl:attribute name="onclick">
                    <xsl:value-of
                       select="concat('renderForm(', $apos, 'sm', $id, $apos, ',', $xp, ',', $dupe, ');')" />
                </xsl:attribute>
                <xsl:attribute name="title">Duplicate Pairing</xsl:attribute>
            </img>
		</li>
	</xsl:template>
    <xsl:template match="scaled">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
        <xsl:variable name="xp"
            select="concat($apos, 'measures/scaled_measures/scaled[@name=&quot;', @name, '&quot;]', $apos)" />
        <li>
            <xsl:attribute name="title">
                <xsl:value-of select="@description" />
            </xsl:attribute>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <xsl:call-template name="CamelCaseWord">
                    <xsl:with-param name="text" select="@name"/>
                </xsl:call-template>
            </a>
        </li>
    </xsl:template>
    <xsl:template match="setpoint">
        <xsl:param name="index" />
        <xsl:variable name="id" select="concat($index, position())" />
        <xsl:variable name="xp"
            select="concat($apos, 'measures/setpoint_measures/setpoint[@name=&quot;', @name, '&quot;]', $apos)" />
        <li>
            <xsl:attribute name="title">
                <xsl:value-of select="@description" />
            </xsl:attribute>
            <a href="#">
                <xsl:attribute name="id">
                     <xsl:value-of select="concat('sm', $id)" />
                </xsl:attribute>
                <xsl:attribute name="onclick">
                    <xsl:value-of
                    select="concat('renderForm(this.id, ', $xp, ');')" />
                </xsl:attribute>
                <xsl:value-of select="$id" />&#160;
                <xsl:call-template name="CamelCaseWord">
                    <xsl:with-param name="text" select="@name"/>
                </xsl:call-template>
            </a>
        </li>
    </xsl:template>
    <xsl:template name="CamelCaseWord">
	    <xsl:param name="text"/>
	    <xsl:value-of
	        select="translate(substring($text, 1, 1), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')"/>
	    <xsl:value-of
	        select="translate(substring($text, 2), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')" />
    </xsl:template>
</xsl:stylesheet>
