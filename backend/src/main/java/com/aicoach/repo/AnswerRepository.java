package com.aicoach.repo;

import com.aicoach.domain.AnswerEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AnswerRepository extends JpaRepository<AnswerEntity, Long> {
    Optional<AnswerEntity> findByQuestion_Id(Long questionId);
}
