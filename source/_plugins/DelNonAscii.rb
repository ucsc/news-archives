module Jekyll
  module DelNonAscii
    def deleteNonAscii(text)
    	encoding_options = {
    		:invalid           => :replace,  # Replace invalid byte sequences
    		:undef             => :replace,  # Replace anything not defined in ASCII
    		:replace           => '',        # Use a blank for those replacements
    		:universal_newline => true       # Always break lines with \n
  		}
  		text.encode(Encoding.find('ASCII'), encoding_options)
      	#text.gsub!(/\P{ASCII}/, '')
    end
  end
end

Liquid::Template.register_filter(Jekyll::DelNonAscii)