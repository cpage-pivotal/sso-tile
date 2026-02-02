package org.tanzu.ssotile.greeting;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.Map;

@Controller
public class GreetingController {

    @GetMapping("/")
    public String greeting(@AuthenticationPrincipal OAuth2User user, Model model) {
        String name = "Guest";
        
        if (user != null) {
            Map<String, Object> attributes = user.getAttributes();
            
            // Try various common claim names for user's name
            name = getFirstNonBlank(attributes,
                    "name",           // Standard OIDC
                    "user_name",      // UAA style
                    "username",       // Common alternative
                    "preferred_username", // OIDC
                    "email",          // Fallback
                    "sub"             // Last resort - subject identifier
            );
            
            if (name == null || name.isBlank()) {
                name = user.getName(); // Spring Security's getName()
            }
        }
        
        model.addAttribute("name", name != null && !name.isBlank() ? name : "Guest");
        return "greeting";
    }
    
    private String getFirstNonBlank(Map<String, Object> attributes, String... keys) {
        for (String key : keys) {
            Object value = attributes.get(key);
            if (value instanceof String s && !s.isBlank()) {
                return s;
            }
        }
        return null;
    }
}
