package com.aicoach.config;

import io.github.cdimascio.dotenv.Dotenv;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.env.EnvironmentPostProcessor;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.core.env.MapPropertySource;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;

/**
 * Loads {@code .env} from the process working directory (e.g. {@code backend/}) before
 * {@code DataSource} properties bind, so {@code DB_PASSWORD} and friends apply to MySQL.
 */
public class DotenvEnvironmentPostProcessor implements EnvironmentPostProcessor {

    @Override
    public void postProcessEnvironment(ConfigurableEnvironment environment, SpringApplication application) {
        Path dir = Path.of(System.getProperty("user.dir", ".")).toAbsolutePath().normalize();
        Path envFile = dir.resolve(".env");
        if (!Files.isRegularFile(envFile)) {
            return;
        }
        Dotenv dotenv = Dotenv.configure()
                .directory(dir.toString())
                .ignoreIfMalformed()
                .ignoreIfMissing()
                .load();

        Map<String, Object> map = new HashMap<>();
        dotenv.entries().forEach(e -> {
            String key = e.getKey();
            if (key != null && !key.isBlank()) {
                map.put(key, e.getValue());
            }
        });
        if (!map.isEmpty()) {
            environment.getPropertySources().addFirst(new MapPropertySource("dotenv", map));
        }
    }
}
